"""Sozlamalar: prices, location, aksiyalar and the booking username."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import PHOTO, VIDEO
from bot.handlers import ui
from bot.keyboards.admin import promos_admin_kb, settings_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import promos, service, slots
from bot.states import AddPromo, EditHours, EditLocation, EditPrice, EditUsername
from bot.timeutil import format_time, parse_time

router = Router()
_BACK = "back:settings"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


def _with_notice(text: str, notice: str | None) -> str:
    """Fold a "saved" confirmation into the next screen rather than leaving it
    behind as its own message."""
    return f"{notice}\n\n{text}" if notice else text


# --- Settings screen --------------------------------------------------------

async def _settings_content(session_factory, lang: str, notice: str | None = None):
    async with session_factory() as session:
        svc = await service.get_service(session)
        promo_count = len(await promos.list_promos(session))
    yes, no = t("value_set", lang), t("value_not_set", lang)
    hours = no
    if slots.has_hours(svc):
        hours = (f"{format_time(svc.open_hour, svc.open_minute)}"
                 f"–{format_time(svc.close_hour, svc.close_minute)}")
    text = t(
        "settings_title", lang,
        price=yes if (svc and svc.price_text) else no,
        hours=hours,
        location=yes if service.has_location(svc) else no,
        promos=promo_count,
        username=f"@{svc.booking_username}" if (svc and svc.booking_username) else no,
    )
    return _with_notice(text, notice), settings_kb(lang)


@router.message(Command("service"))
async def cmd_service(message: Message, lang: str, session_factory):
    await ui.drop(message)
    if not _is_admin(message.from_user.id):
        await ui.send(message, t("not_authorized", lang))
        return
    text, markup = await _settings_content(session_factory, lang)
    await ui.show_screen(message, text, markup)


@router.callback_query(F.data.in_({"adm:settings", "back:settings"}))
async def panel_settings(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.clear()
    text, markup = await _settings_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


async def _settings_after_save(message: Message, session_factory, lang: str, notice: str) -> None:
    text, markup = await _settings_content(session_factory, lang, notice=notice)
    await ui.replace_screen(message, text, markup)


# --- Narxlar ----------------------------------------------------------------

@router.callback_query(F.data == "adm:price")
async def edit_price(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    async with session_factory() as session:
        svc = await service.get_service(session)
    current = svc.price_text if (svc and svc.price_text) else "—"
    await state.set_state(EditPrice.text)
    await ui.edit_screen(cb, t("ask_price", lang, current=current), back_kb(_BACK, lang))
    await cb.answer()


@router.message(EditPrice.text, F.text)
async def save_price(message: Message, state: FSMContext, lang: str, session_factory):
    async with session_factory() as session:
        await service.set_price(session, message.text.strip())
    await state.clear()
    await _settings_after_save(message, session_factory, lang, t("price_saved", lang))


# --- Working hours ----------------------------------------------------------

@router.callback_query(F.data == "adm:hours")
async def edit_hours(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.set_state(EditHours.open_at)
    await ui.edit_screen(cb, t("ask_open_hour", lang), back_kb(_BACK, lang))
    await cb.answer()


@router.message(EditHours.open_at, F.text)
async def save_open(message: Message, state: FSMContext, lang: str):
    minutes = parse_time(message.text)
    if minutes is None or minutes >= 24 * 60:
        await ui.replace_screen(message, t("hour_invalid", lang), back_kb(_BACK, lang))
        return
    await state.update_data(open_at=minutes)
    await state.set_state(EditHours.close_at)
    await ui.replace_screen(message, t("ask_close_hour", lang), back_kb(_BACK, lang))


@router.message(EditHours.close_at, F.text)
async def save_close(message: Message, state: FSMContext, lang: str, session_factory):
    minutes = parse_time(message.text)
    data = await state.get_data()
    if minutes is None or minutes <= data["open_at"]:
        await ui.replace_screen(message, t("hour_invalid", lang), back_kb(_BACK, lang))
        return
    async with session_factory() as session:
        await service.set_hours(
            session,
            open_hour=data["open_at"] // 60, open_minute=data["open_at"] % 60,
            close_hour=minutes // 60, close_minute=minutes % 60,
        )
    await state.clear()
    await _settings_after_save(message, session_factory, lang, t("hours_saved", lang))


# --- Location ---------------------------------------------------------------

@router.callback_query(F.data == "adm:location")
async def edit_location(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.set_state(EditLocation.value)
    await ui.edit_screen(cb, t("ask_location", lang), back_kb(_BACK, lang))
    await cb.answer()


@router.message(EditLocation.value)
async def save_location(message: Message, state: FSMContext, lang: str, session_factory):
    title = address = latitude = longitude = url = None
    # A venue carries a .location too, so it has to be checked first or the
    # title/address would be dropped.
    if message.venue:
        latitude = message.venue.location.latitude
        longitude = message.venue.location.longitude
        title, address = message.venue.title, message.venue.address
    elif message.location:
        latitude, longitude = message.location.latitude, message.location.longitude
    elif message.text and message.text.strip().lower().startswith(("http://", "https://")):
        url = message.text.strip()
    else:
        await ui.replace_screen(message, t("location_invalid", lang), back_kb(_BACK, lang))
        return
    async with session_factory() as session:
        await service.set_location(
            session, title=title, address=address,
            latitude=latitude, longitude=longitude, location_url=url,
        )
    await state.clear()
    await _settings_after_save(message, session_factory, lang, t("location_saved", lang))


# --- Booking username -------------------------------------------------------

@router.callback_query(F.data == "adm:username")
async def edit_username(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    async with session_factory() as session:
        svc = await service.get_service(session)
    current = f"@{svc.booking_username}" if (svc and svc.booking_username) else "—"
    await state.set_state(EditUsername.value)
    await ui.edit_screen(cb, t("ask_username", lang, current=current), back_kb(_BACK, lang))
    await cb.answer()


@router.message(EditUsername.value, F.text)
async def save_username(message: Message, state: FSMContext, lang: str, session_factory):
    username = service.normalize_username(message.text)
    if username is None:
        await ui.replace_screen(message, t("username_invalid", lang), back_kb(_BACK, lang))
        return
    async with session_factory() as session:
        await service.set_booking_username(session, username)
    await state.clear()
    await _settings_after_save(
        message, session_factory, lang, t("username_saved", lang, username=username)
    )


# --- Aksiyalar --------------------------------------------------------------

async def _promos_content(session_factory, lang: str, notice: str | None = None):
    async with session_factory() as session:
        items = await promos.list_promos(session)
    text = t("promos_admin_title", lang, count=len(items))
    return _with_notice(text, notice), promos_admin_kb(items, lang)


@router.callback_query(F.data.in_({"adm:promos", "back:promos"}))
async def panel_promos(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.clear()
    text, markup = await _promos_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


@router.callback_query(F.data == "promo:add")
async def add_promo_start(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.set_state(AddPromo.text)
    await ui.edit_screen(cb, t("ask_promo_text", lang), back_kb("back:promos", lang))
    await cb.answer()


@router.message(AddPromo.text, F.text)
async def add_promo_text(message: Message, state: FSMContext, lang: str):
    await state.update_data(text=message.text.strip())
    await state.set_state(AddPromo.media)
    await ui.replace_screen(message, t("ask_promo_media", lang), back_kb("back:promos", lang))


@router.message(AddPromo.media)
async def add_promo_media(message: Message, state: FSMContext, lang: str, session_factory):
    media_type = file_id = None
    if message.photo:
        media_type, file_id = PHOTO, message.photo[-1].file_id  # largest size
    elif message.video:
        media_type, file_id = VIDEO, message.video.file_id
    elif message.text and message.text.strip() == "-":
        pass
    else:
        await ui.replace_screen(message, t("promo_media_invalid", lang),
                                back_kb("back:promos", lang))
        return
    data = await state.get_data()
    async with session_factory() as session:
        await promos.add_promo(session, data["text"], media_type, file_id)
    await state.clear()
    text, markup = await _promos_content(session_factory, lang, notice=t("promo_saved", lang))
    await ui.replace_screen(message, text, markup)


@router.callback_query(F.data.startswith("promo:del:"))
async def delete_promo(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    promo_id = int(cb.data.split(":")[2])
    async with session_factory() as session:
        await promos.delete_promo(session, promo_id)
    text, markup = await _promos_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer(t("promo_deleted", lang))
