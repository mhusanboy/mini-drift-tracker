"""The admin's booking-request card: accept, reject, edit.

Everything happens inside the one card message. An edit turns the card into a
prompt; the admin's typed answer is deleted and the card is rebuilt in its
place, so the notification never spawns a trail of messages.
"""
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import BookingStatus
from bot.handlers import ui
from bot.keyboards.booking import card_back_kb, card_conflict_kb, card_edit_kb, card_kb
from bot.locales import t
from bot.services import bookings, notify, slots, whenparse
from bot.states import EditCard
from bot.timeutil import fmt_minutes

router = Router()

MAX_DURATION_HOURS = 12


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _load(cb: CallbackQuery, session_factory, lang: str):
    """The booking a card callback refers to, or None (with the admin told)."""
    async with session_factory() as session:
        booking = await bookings.get(session, int(cb.data.split(":")[-1]))
    if booking is None:
        await cb.answer(t("card_gone", lang), show_alert=True)
    return booking


async def _render(cb: CallbackQuery, booking, lang: str) -> None:
    await ui.edit_card(cb, notify.card_text(booking, lang), card_kb(booking, lang))


# --- Decide -----------------------------------------------------------------

async def _decide(cb: CallbackQuery, booking_id: int, status: str, lang: str,
                  session_factory, toast: str) -> None:
    async with session_factory() as session:
        booking = await bookings.set_status(session, booking_id, status)
    if booking is None:
        await cb.answer(t("card_gone", lang), show_alert=True)
        return
    await _render(cb, booking, lang)
    await cb.answer(t(toast, lang))


@router.callback_query(F.data.startswith("bk:accept:"))
async def accept(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    booking = await _load(cb, session_factory, lang)
    if booking is None:
        return
    if booking.date is None or booking.start_minute is None:
        await cb.answer(t("card_no_time", lang), show_alert=True)
        return
    async with session_factory() as session:
        clashes = await slots.conflicts_for(session, booking)
    if clashes:
        # The admin may genuinely want two groups at once — warn, don't refuse.
        rows = "\n".join(
            t("card_conflict_row", lang,
              start=fmt_minutes(c.start_minute),
              end=fmt_minutes(c.start_minute + c.duration_hours * 60),
              name=c.full_name, people=c.people_count)
            for c in clashes
        )
        await ui.edit_card(cb, t("card_conflict", lang, rows=rows),
                           card_conflict_kb(booking.id, lang))
        await cb.answer()
        return
    await _decide(cb, booking.id, BookingStatus.ACCEPTED, lang, session_factory,
                  "card_accepted_toast")


@router.callback_query(F.data.startswith("bk:force:"))
async def accept_anyway(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _decide(cb, int(cb.data.split(":")[-1]), BookingStatus.ACCEPTED, lang,
                  session_factory, "card_accepted_toast")


@router.callback_query(F.data.startswith("bk:reject:"))
async def reject(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _decide(cb, int(cb.data.split(":")[-1]), BookingStatus.REJECTED, lang,
                  session_factory, "card_rejected_toast")


# --- Navigation within the card ---------------------------------------------

@router.callback_query(F.data.startswith("bk:card:"))
async def back_to_card(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.clear()
    booking = await _load(cb, session_factory, lang)
    if booking is None:
        return
    await _render(cb, booking, lang)
    await cb.answer()


@router.callback_query(F.data.startswith("bk:edit:"))
async def edit_menu(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    booking = await _load(cb, session_factory, lang)
    if booking is None:
        return
    await ui.edit_card(cb, t("card_edit_title", lang), card_edit_kb(booking, lang))
    await cb.answer()


# --- Edits ------------------------------------------------------------------

_PROMPTS = {
    "time": (EditCard.time, "card_ask_time"),
    "dur": (EditCard.duration, "card_ask_duration"),
    "people": (EditCard.people, "card_ask_people"),
}


@router.callback_query(F.data.startswith("bk:set:"))
async def ask_field(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    _, _, field, raw_id = cb.data.split(":")
    booking = await _load(cb, session_factory, lang)
    if booking is None:
        return
    state_name, prompt = _PROMPTS[field]
    # Remember which message to rebuild once the answer is typed.
    await state.update_data(
        booking_id=booking.id, card_chat=cb.message.chat.id, card_id=cb.message.message_id,
    )
    await state.set_state(state_name)
    await ui.edit_card(cb, t(prompt, lang), card_back_kb(booking.id, lang))
    await cb.answer()


async def _reject_input(message: Message, state: FSMContext, lang: str, key: str) -> None:
    """Drop what the admin typed and leave the prompt showing why."""
    data = await state.get_data()
    await ui.drop(message)
    await ui.edit_message(
        message.bot, data["card_chat"], data["card_id"], t(key, lang),
        card_back_kb(data["booking_id"], lang),
    )


async def _restore_card(message: Message, state: FSMContext, booking, lang: str) -> None:
    data = await state.get_data()
    await ui.drop(message)
    await ui.edit_message(
        message.bot, data["card_chat"], data["card_id"],
        notify.card_text(booking, lang), card_kb(booking, lang),
    )
    await state.clear()


@router.message(EditCard.time, F.text)
async def save_time(message: Message, state: FSMContext, lang: str, session_factory):
    day, start_minute = whenparse.parse_when(message.text, date.today())
    if start_minute is None:
        await _reject_input(message, state, lang, "card_time_invalid")
        return
    data = await state.get_data()
    async with session_factory() as session:
        booking = await bookings.set_time(session, data["booking_id"], day, start_minute)
    await _restore_card(message, state, booking, lang)


@router.message(EditCard.duration, F.text)
async def save_duration(message: Message, state: FSMContext, lang: str, session_factory):
    entered = message.text.strip()
    if not entered.isdigit() or not 1 <= int(entered) <= MAX_DURATION_HOURS:
        await _reject_input(message, state, lang, "card_duration_invalid")
        return
    data = await state.get_data()
    async with session_factory() as session:
        booking = await bookings.set_duration(session, data["booking_id"], int(entered))
    await _restore_card(message, state, booking, lang)


@router.message(EditCard.people, F.text)
async def save_people(message: Message, state: FSMContext, lang: str, session_factory):
    entered = message.text.strip()
    if not entered.isdigit() or int(entered) < 1:
        await _reject_input(message, state, lang, "people_invalid")
        return
    data = await state.get_data()
    async with session_factory() as session:
        booking = await bookings.set_people(session, data["booking_id"], int(entered))
    await _restore_card(message, state, booking, lang)
