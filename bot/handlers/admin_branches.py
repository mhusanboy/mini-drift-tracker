from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import Branch
from bot.keyboards.admin import admin_branches_kb
from bot.locales import t
from bot.states import AddBranch
from bot.timeutil import format_time, parse_time

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_branches(target, session_factory, lang: str):
    async with session_factory() as session:
        branches = list((await session.execute(select(Branch).order_by(Branch.name))).scalars().all())
    lines = [
        t("branch_admin_line", lang,
          status=("🟢" if b.is_active else "🔴") + (
              "📍" if (b.location_url or b.latitude is not None) else ""),
          name=b.name,
          open=format_time(b.open_hour, b.open_minute),
          close=format_time(b.close_hour, b.close_minute), address=b.address)
        for b in branches
    ] or ["—"]
    await target.answer(
        t("branches_title", lang) + "\n" + "\n".join(lines),
        reply_markup=admin_branches_kb(branches, lang),
    )


@router.message(Command("branches"))
async def cmd_branches(message: Message, lang: str, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _render_branches(message, session_factory, lang)


@router.callback_query(F.data == "adm:branches")
async def panel_branches(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _render_branches(cb.message, session_factory, lang)
    await cb.answer()


@router.callback_query(F.data == "abranch:add")
async def add_branch(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=None)
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", lang))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:edit:"))
async def edit_branch(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=int(cb.data.split(":")[2]))
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", lang))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:toggle:"))
async def toggle_branch(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    branch_id = int(cb.data.split(":")[2])
    async with session_factory() as session:
        branch = await session.get(Branch, branch_id)
        if branch:
            branch.is_active = not branch.is_active
            await session.commit()
    await cb.answer(t("branch_toggled", lang))
    await _render_branches(cb.message, session_factory, lang)


@router.message(AddBranch.name, F.text)
async def branch_name(message: Message, state: FSMContext, lang: str):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddBranch.address)
    await message.answer(t("ask_branch_address", lang))


@router.message(AddBranch.address, F.text)
async def branch_address(message: Message, state: FSMContext, lang: str):
    await state.update_data(address=message.text.strip())
    await state.set_state(AddBranch.open_hour)
    await message.answer(t("ask_open_hour", lang))


@router.message(AddBranch.open_hour, F.text)
async def branch_open(message: Message, state: FSMContext, lang: str):
    minutes = parse_time(message.text)
    # Opening must be a real time-of-day (not 24:00 midnight).
    if minutes is None or minutes >= 24 * 60:
        await message.answer(t("hour_invalid", lang))
        return
    await state.update_data(open_hour=minutes // 60, open_minute=minutes % 60)
    await state.set_state(AddBranch.close_hour)
    await message.answer(t("ask_close_hour", lang))


@router.message(AddBranch.close_hour, F.text)
async def branch_close(message: Message, state: FSMContext, lang: str):
    minutes = parse_time(message.text)
    data = await state.get_data()
    open_minutes = data["open_hour"] * 60 + data["open_minute"]
    if minutes is None or minutes <= open_minutes:
        await message.answer(t("hour_invalid", lang))
        return
    await state.update_data(close_hour=minutes // 60, close_minute=minutes % 60)
    await state.set_state(AddBranch.location)
    await message.answer(t("ask_branch_location", lang))


async def _finalize_branch(message, state, lang, session_factory, latitude, longitude, url):
    data = await state.get_data()
    async with session_factory() as session:
        if data.get("edit_id"):
            branch = await session.get(Branch, data["edit_id"])
            branch.name = data["name"]
            branch.address = data["address"]
            branch.open_hour = data["open_hour"]
            branch.open_minute = data["open_minute"]
            branch.close_hour = data["close_hour"]
            branch.close_minute = data["close_minute"]
            branch.latitude = latitude
            branch.longitude = longitude
            branch.location_url = url
        else:
            session.add(Branch(
                name=data["name"], address=data["address"],
                open_hour=data["open_hour"], open_minute=data["open_minute"],
                close_hour=data["close_hour"], close_minute=data["close_minute"],
                latitude=latitude, longitude=longitude, location_url=url, is_active=True,
            ))
        await session.commit()
    await state.clear()
    await message.answer(t("branch_saved", lang))
    await _render_branches(message, session_factory, lang)


@router.message(AddBranch.location)
async def branch_location(message: Message, state: FSMContext, lang: str, session_factory):
    latitude = longitude = url = None
    if message.location:
        latitude, longitude = message.location.latitude, message.location.longitude
    elif message.venue:
        latitude, longitude = message.venue.location.latitude, message.venue.location.longitude
    elif message.text and message.text.strip() == "-":
        pass  # skip — leave location empty
    elif message.text and message.text.strip().lower().startswith(("http://", "https://")):
        url = message.text.strip()
    else:
        await message.answer(t("location_invalid", lang))
        return
    await _finalize_branch(message, state, lang, session_factory, latitude, longitude, url)
