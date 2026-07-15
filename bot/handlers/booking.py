from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import User
from bot.handlers.ui import edit_screen
from bot.keyboards.booking import confirm_kb, days_kb, slots_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import notify, slots
from bot.states import Booking
from bot.timeutil import fmt_minutes

router = Router()


def _now() -> datetime:
    return datetime.now()


async def _show_days(cb: CallbackQuery, state: FSMContext, lang: str, session_factory) -> None:
    async with session_factory() as session:
        service = await slots.get_service(session)
        if service is None:
            await cb.answer(t("service_unavailable", lang), show_alert=True)
            return
        days = await slots.bookable_days(session, _now().date())
    if not days:
        await cb.answer(t("no_available_days", lang), show_alert=True)
        return
    await state.update_data(branch_id=service.id)
    await state.set_state(Booking.day)
    await edit_screen(cb, t("choose_day", lang), days_kb(days, _now().date(), lang))
    await cb.answer()


@router.callback_query(F.data == "menu:book")
async def start_booking(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    await _show_days(cb, state, lang, session_factory)


@router.callback_query(F.data == "back:days")
async def back_to_days(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    await _show_days(cb, state, lang, session_factory)


async def _show_slots(cb: CallbackQuery, state: FSMContext, lang: str, session_factory) -> None:
    data = await state.get_data()
    if "branch_id" not in data or "day" not in data:
        await _show_days(cb, state, lang, session_factory)
        return
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        service = await slots.get_branch(session, data["branch_id"])
        offs = await slots.day_offs_in(session, [day])
        avail = await slots.free_slots(session, service, day, _now(), day_off=(day in offs))
    if not avail:
        await cb.answer(t("no_slots", lang), show_alert=True)
        return
    await state.set_state(Booking.time)
    await edit_screen(cb, t("choose_time", lang), slots_kb(avail, lang))
    await cb.answer()


@router.callback_query(F.data == "back:times")
async def back_to_times(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    await _show_slots(cb, state, lang, session_factory)


@router.callback_query(Booking.day, F.data.startswith("day:"))
async def pick_day(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    day = date.fromisoformat(cb.data.split(":", 1)[1])
    await state.update_data(day=day.isoformat())
    await _show_slots(cb, state, lang, session_factory)


@router.callback_query(Booking.time, F.data.startswith("slot:"))
async def pick_slot(cb: CallbackQuery, state: FSMContext, lang: str):
    start_minute = int(cb.data.split(":")[1])
    await state.update_data(start_minute=start_minute)
    await state.set_state(Booking.people)
    await edit_screen(cb, t("ask_people", lang), back_kb("back:times", lang))
    await cb.answer()


@router.message(Booking.people, F.text)
async def enter_people(message: Message, state: FSMContext, lang: str, session_factory):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer(t("people_invalid", lang), reply_markup=back_kb("back:times", lang))
        return
    people = int(text)
    num_hours = slots.hours_needed(people)
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        service = await slots.get_branch(session, data["branch_id"])
        if not slots.span_fits(service, data["start_minute"], num_hours):
            avail = await slots.free_slots(session, service, day, _now())
            if avail:
                await state.set_state(Booking.time)
                await message.answer(t("not_enough_time", lang, hours=num_hours),
                                     reply_markup=slots_kb(avail, lang))
            else:
                days = await slots.bookable_days(session, _now().date())
                await state.set_state(Booking.day)
                await message.answer(t("no_slots", lang),
                                     reply_markup=days_kb(days, _now().date(), lang))
            return
    await state.update_data(people=people)
    await state.set_state(Booking.confirm)
    await message.answer(
        t("confirm_title", lang, date=data["day"],
          time=fmt_minutes(data["start_minute"]), people=people),
        reply_markup=confirm_kb(lang),
    )


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def confirm_yes(cb: CallbackQuery, state: FSMContext, lang: str, bot: Bot, session_factory):
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        booking = await slots.create_booking(
            session, cb.from_user.id, data["branch_id"], day, data["start_minute"], data["people"]
        )
        if booking is None:
            service = await slots.get_branch(session, data["branch_id"])
            avail = await slots.free_slots(session, service, day, _now())
            await state.set_state(Booking.time)
            await edit_screen(cb, t("slot_taken", lang), slots_kb(avail, lang))
            await cb.answer()
            return
        user = await session.get(User, cb.from_user.id)
    await state.clear()
    await edit_screen(
        cb,
        t("booking_confirmed", lang, date=data["day"], time=fmt_minutes(data["start_minute"])),
        back_kb("back:main", lang),
    )
    await notify.notify_new_booking(bot, session_factory, get_settings().admin_ids, booking, user)
    await cb.answer()
