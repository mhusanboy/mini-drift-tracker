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

router = Router()
LANG = "ru"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_branches(target, session_factory):
    async with session_factory() as session:
        branches = list((await session.execute(select(Branch).order_by(Branch.name))).scalars().all())
    lines = [
        t("branch_admin_line", LANG,
          status="🟢" if b.is_active else "🔴", name=b.name,
          open=b.open_hour, close=b.close_hour, address=b.address)
        for b in branches
    ] or ["—"]
    await target.answer(
        t("branches_title", LANG) + "\n" + "\n".join(lines),
        reply_markup=admin_branches_kb(branches, LANG),
    )


@router.message(Command("branches"))
async def cmd_branches(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    await _render_branches(message, session_factory)


@router.callback_query(F.data == "abranch:add")
async def add_branch(cb: CallbackQuery, state: FSMContext):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=None)
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", LANG))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:edit:"))
async def edit_branch(cb: CallbackQuery, state: FSMContext):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=int(cb.data.split(":")[2]))
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", LANG))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:toggle:"))
async def toggle_branch(cb: CallbackQuery, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    branch_id = int(cb.data.split(":")[2])
    async with session_factory() as session:
        branch = await session.get(Branch, branch_id)
        if branch:
            branch.is_active = not branch.is_active
            await session.commit()
    await cb.answer(t("branch_toggled", LANG))
    await _render_branches(cb.message, session_factory)


@router.message(AddBranch.name, F.text)
async def branch_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddBranch.address)
    await message.answer(t("ask_branch_address", LANG))


@router.message(AddBranch.address, F.text)
async def branch_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(AddBranch.open_hour)
    await message.answer(t("ask_open_hour", LANG))


@router.message(AddBranch.open_hour, F.text)
async def branch_open(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 23):
        await message.answer(t("hour_invalid", LANG))
        return
    await state.update_data(open_hour=int(text))
    await state.set_state(AddBranch.close_hour)
    await message.answer(t("ask_close_hour", LANG))


@router.message(AddBranch.close_hour, F.text)
async def branch_close(message: Message, state: FSMContext, session_factory):
    text = message.text.strip()
    data = await state.get_data()
    if not text.isdigit() or not (1 <= int(text) <= 24) or int(text) <= data["open_hour"]:
        await message.answer(t("hour_invalid", LANG))
        return
    close_hour = int(text)
    async with session_factory() as session:
        if data.get("edit_id"):
            branch = await session.get(Branch, data["edit_id"])
            branch.name = data["name"]
            branch.address = data["address"]
            branch.open_hour = data["open_hour"]
            branch.close_hour = close_hour
        else:
            session.add(Branch(
                name=data["name"], address=data["address"],
                open_hour=data["open_hour"], close_hour=close_hour, is_active=True,
            ))
        await session.commit()
    await state.clear()
    await message.answer(t("branch_saved", LANG))
    await _render_branches(message, session_factory)
