"""The customer menu: Location, Narxlar, Aksiyalar, Bron qilish."""
from datetime import date

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import PHOTO, VIDEO, User
from bot.handlers import ui
from bot.keyboards.common import back_kb, booking_link_kb, main_menu_kb
from bot.locales import t
from bot.services import booking_link, bookings, notify, promos, service, whenparse
from bot.states import BookingRequest
from bot.timeutil import today_local

router = Router()

# Telegram rejects a media caption longer than this.
CAPTION_LIMIT = 1024


async def _menu_below(message: Message, user_id: int, lang: str) -> None:
    """Pins and photos can't live inside a text screen, so they are sent above a
    fresh menu — which becomes the screen the next tap replaces."""
    is_admin = get_settings().is_admin(user_id)
    await ui.send(message, t("main_menu_title", lang), main_menu_kb(lang, is_admin))


# --- Location ---------------------------------------------------------------

@router.callback_query(F.data == "menu:location")
async def show_location(cb: CallbackQuery, lang: str, session_factory):
    async with session_factory() as session:
        svc = await service.get_service(session)
    if not service.has_location(svc):
        await cb.answer(t("location_not_set", lang), show_alert=True)
        return
    await ui.purge(cb.bot, cb.message.chat.id)
    if svc.latitude is not None and svc.longitude is not None:
        if svc.title:
            ui.own(await cb.message.answer_venue(
                latitude=svc.latitude, longitude=svc.longitude,
                title=svc.title, address=svc.address or svc.title,
            ))
        else:
            ui.own(await cb.message.answer_location(
                latitude=svc.latitude, longitude=svc.longitude,
            ))
    else:
        await ui.send(cb.message, t("location_link", lang, url=svc.location_url))
    await _menu_below(cb.message, cb.from_user.id, lang)
    await cb.answer()


# --- Narxlar ----------------------------------------------------------------

@router.callback_query(F.data == "menu:prices")
async def show_prices(cb: CallbackQuery, lang: str, session_factory):
    async with session_factory() as session:
        svc = await service.get_service(session)
    if svc is None or not svc.price_text:
        await cb.answer(t("prices_not_set", lang), show_alert=True)
        return
    await ui.edit_screen(cb, svc.price_text, back_kb("back:main", lang))
    await cb.answer()


# --- Aksiyalar --------------------------------------------------------------

async def _send_promo(message: Message, promo) -> None:
    """Text as the media caption when it fits, otherwise as its own message."""
    has_media = promo.media_type in (PHOTO, VIDEO) and promo.file_id
    caption = promo.text if len(promo.text) <= CAPTION_LIMIT else None
    if has_media:
        if promo.media_type == PHOTO:
            ui.own(await message.answer_photo(promo.file_id, caption=caption))
        else:
            ui.own(await message.answer_video(promo.file_id, caption=caption))
    if caption is None or not has_media:
        await ui.send(message, promo.text)


@router.callback_query(F.data == "menu:promos")
async def show_promos(cb: CallbackQuery, lang: str, session_factory):
    async with session_factory() as session:
        items = await promos.list_promos(session)
    if not items:
        await cb.answer(t("promos_empty", lang), show_alert=True)
        return
    await ui.purge(cb.bot, cb.message.chat.id)
    await ui.send(cb.message, t("promos_title", lang))
    for promo in items:
        await _send_promo(cb.message, promo)
    await _menu_below(cb.message, cb.from_user.id, lang)
    await cb.answer()


# --- Bron qilish ------------------------------------------------------------

@router.callback_query(F.data == "menu:book")
async def start_booking(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    async with session_factory() as session:
        svc = await service.get_service(session)
    if svc is None or not svc.booking_username:
        await cb.answer(t("booking_unavailable", lang), show_alert=True)
        return
    await state.set_state(BookingRequest.when)
    await ui.edit_screen(cb, t("ask_booking_when", lang), back_kb("back:main", lang))
    await cb.answer()


@router.message(BookingRequest.when, F.text)
async def booking_when(message: Message, state: FSMContext, lang: str, user: User | None,
                       session_factory):
    if user is None:  # not registered — nothing to put in the template
        await state.clear()
        return
    when = message.text.strip()
    if not when or len(when) > booking_link.MAX_WHEN_LEN:
        await ui.replace_screen(message, t("booking_when_too_long", lang),
                                back_kb("back:main", lang))
        return
    # Understood or not, the request goes through — an unreadable time just
    # arrives at the admin flagged for them to set.
    day, start_minute = whenparse.parse_when(when, today_local())
    await state.update_data(
        when_text=when,
        day=day.isoformat() if day else None,
        start_minute=start_minute,
    )
    await state.set_state(BookingRequest.people)
    await ui.replace_screen(message, t("ask_booking_people", lang), back_kb("back:main", lang))


@router.message(BookingRequest.people, F.text)
async def booking_people(message: Message, state: FSMContext, lang: str, user: User | None,
                         bot: Bot, session_factory):
    if user is None:
        await state.clear()
        return
    entered = message.text.strip()
    if not entered.isdigit() or int(entered) < 1:
        await ui.replace_screen(message, t("people_invalid", lang), back_kb("back:main", lang))
        return
    people = int(entered)
    data = await state.get_data()
    async with session_factory() as session:
        svc = await service.get_service(session)
    if svc is None or not svc.booking_username:
        await state.clear()
        await ui.replace_screen(message, t("booking_unavailable", lang),
                                back_kb("back:main", lang))
        return
    async with session_factory() as session:
        booking = await bookings.create(
            session, user, data["when_text"], people,
            date.fromisoformat(data["day"]) if data.get("day") else None,
            data.get("start_minute"),
        )
    await state.clear()
    text, url = booking_link.build(
        lang, svc.booking_username, user.full_name, user.phone, data["when_text"], people
    )
    await ui.replace_screen(message, t("booking_link_intro", lang, message=text),
                            booking_link_kb(url, lang))
    # The bot cannot see the deep link being tapped, so the admin is told as
    # soon as the request is complete — whether or not the DM ever arrives.
    await notify.send_request(bot, session_factory, get_settings().admin_ids, booking)
