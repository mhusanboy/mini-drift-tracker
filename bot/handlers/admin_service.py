from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.admin import service_edit_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import slots
from bot.states import EditService
from bot.timeutil import format_time, parse_time

router = Router()
_BACK = "back:service"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_service(target, session_factory, lang: str) -> None:
    async with session_factory() as session:
        service = await slots.get_service(session)
    if service is None:
        await target.answer(t("service_not_set", lang), reply_markup=service_edit_kb(lang))
        return
    loc = "📍" if (service.location_url or service.latitude is not None) else "—"
    await target.answer(
        t("service_line", lang, name=service.name, address=service.address,
          open=format_time(service.open_hour, service.open_minute),
          close=format_time(service.close_hour, service.close_minute), loc=loc),
        reply_markup=service_edit_kb(lang),
    )


@router.message(Command("service"))
async def cmd_service(message: Message, lang: str, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _render_service(message, session_factory, lang)


@router.callback_query(F.data == "adm:service")
async def panel_service(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _render_service(cb.message, session_factory, lang)
    await cb.answer()


@router.callback_query(F.data == "adm:service:edit")
async def edit_service(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.set_state(EditService.name)
    await cb.message.answer(t("ask_service_name", lang), reply_markup=back_kb(_BACK, lang))
    await cb.answer()


@router.callback_query(F.data == "back:service")
async def back_to_service(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    await state.clear()
    await _render_service(cb.message, session_factory, lang)
    await cb.answer()


@router.message(EditService.name, F.text)
async def service_name(message: Message, state: FSMContext, lang: str):
    await state.update_data(name=message.text.strip())
    await state.set_state(EditService.address)
    await message.answer(t("ask_service_address", lang), reply_markup=back_kb(_BACK, lang))


@router.message(EditService.address, F.text)
async def service_address(message: Message, state: FSMContext, lang: str):
    await state.update_data(address=message.text.strip())
    await state.set_state(EditService.open_hour)
    await message.answer(t("ask_open_hour", lang), reply_markup=back_kb(_BACK, lang))


@router.message(EditService.open_hour, F.text)
async def service_open(message: Message, state: FSMContext, lang: str):
    minutes = parse_time(message.text)
    if minutes is None or minutes >= 24 * 60:
        await message.answer(t("hour_invalid", lang), reply_markup=back_kb(_BACK, lang))
        return
    await state.update_data(open_hour=minutes // 60, open_minute=minutes % 60)
    await state.set_state(EditService.close_hour)
    await message.answer(t("ask_close_hour", lang), reply_markup=back_kb(_BACK, lang))


@router.message(EditService.close_hour, F.text)
async def service_close(message: Message, state: FSMContext, lang: str):
    minutes = parse_time(message.text)
    data = await state.get_data()
    if minutes is None or minutes <= data["open_hour"] * 60 + data["open_minute"]:
        await message.answer(t("hour_invalid", lang), reply_markup=back_kb(_BACK, lang))
        return
    await state.update_data(close_hour=minutes // 60, close_minute=minutes % 60)
    await state.set_state(EditService.location)
    await message.answer(t("ask_service_location", lang), reply_markup=back_kb(_BACK, lang))


@router.message(EditService.location)
async def service_location(message: Message, state: FSMContext, lang: str, session_factory):
    latitude = longitude = url = None
    if message.location:
        latitude, longitude = message.location.latitude, message.location.longitude
    elif message.venue:
        latitude, longitude = message.venue.location.latitude, message.venue.location.longitude
    elif message.text and message.text.strip() == "-":
        pass
    elif message.text and message.text.strip().lower().startswith(("http://", "https://")):
        url = message.text.strip()
    else:
        await message.answer(t("location_invalid", lang), reply_markup=back_kb(_BACK, lang))
        return
    data = await state.get_data()
    async with session_factory() as session:
        await slots.upsert_service(
            session, name=data["name"], address=data["address"],
            open_hour=data["open_hour"], open_minute=data["open_minute"],
            close_hour=data["close_hour"], close_minute=data["close_minute"],
            latitude=latitude, longitude=longitude, location_url=url,
        )
    await state.clear()
    await message.answer(t("service_saved", lang))
    await _render_service(message, session_factory, lang)
