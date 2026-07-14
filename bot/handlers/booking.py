from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import User
from bot.keyboards.booking import branches_kb, confirm_kb, days_kb, times_kb
from bot.locales import t
from bot.services import notify, slots
from bot.states import Booking

router = Router()


def _now() -> datetime:
    return datetime.now()


@router.callback_query(F.data == "menu:book")
async def start_booking(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    async with session_factory() as session:
        branches = await slots.list_active_branches(session)
    if not branches:
        await cb.message.answer(t("no_branches", lang))
        await cb.answer()
        return
    await state.set_state(Booking.branch)
    await cb.message.answer(t("choose_branch", lang), reply_markup=branches_kb(branches, lang))
    await cb.answer()


async def _send_branch_location(message, branch, lang: str) -> None:
    """Show the customer where the branch is: a Telegram venue pin if we have
    coordinates, otherwise the saved map link."""
    if branch.latitude is not None and branch.longitude is not None:
        await message.answer_venue(
            latitude=branch.latitude, longitude=branch.longitude,
            title=branch.name, address=branch.address,
        )
    elif branch.location_url:
        await message.answer(t("branch_location_link", lang, name=branch.name,
                              address=branch.address, url=branch.location_url))


@router.callback_query(Booking.branch, F.data.startswith("branch:"))
async def pick_branch(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    branch_id = int(cb.data.split(":")[1])
    await state.update_data(branch_id=branch_id)
    async with session_factory() as session:
        branch = await slots.get_branch(session, branch_id)
    if branch is not None:
        await _send_branch_location(cb.message, branch, lang)
    await state.set_state(Booking.day)
    days = slots.next_days(_now().date())
    await cb.message.answer(t("choose_day", lang), reply_markup=days_kb(days, lang))
    await cb.answer()


@router.callback_query(Booking.day, F.data.startswith("day:"))
async def pick_day(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    day = date.fromisoformat(cb.data.split(":", 1)[1])
    data = await state.get_data()
    async with session_factory() as session:
        branch = await slots.get_branch(session, data["branch_id"])
        hours = await slots.free_hours(session, branch, day, _now())
    if not hours:
        await cb.message.answer(t("no_slots", lang))
        await cb.answer()
        return
    await state.update_data(day=day.isoformat())
    await state.set_state(Booking.time)
    await cb.message.answer(t("choose_time", lang), reply_markup=times_kb(hours, lang))
    await cb.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(cb: CallbackQuery, state: FSMContext, lang: str):
    hour = int(cb.data.split(":")[1])
    await state.update_data(hour=hour)
    await state.set_state(Booking.people)
    await cb.message.answer(t("ask_people", lang))
    await cb.answer()


@router.message(Booking.people, F.text)
async def enter_people(message: Message, state: FSMContext, lang: str, session_factory):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer(t("people_invalid", lang))
        return
    people = int(text)
    num_hours = slots.hours_needed(people)
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        branch = await slots.get_branch(session, data["branch_id"])
        if not slots.span_fits(branch, data["hour"], num_hours):
            # The group needs more consecutive hours than remain before closing.
            hours = await slots.free_hours(session, branch, day, _now())
            if hours:
                await state.set_state(Booking.time)
                await message.answer(t("not_enough_time", lang, hours=num_hours),
                                     reply_markup=times_kb(hours, lang))
            else:
                await state.set_state(Booking.day)
                await message.answer(t("no_slots", lang),
                                     reply_markup=days_kb(slots.next_days(_now().date()), lang))
            return
    await state.update_data(people=people, num_hours=num_hours)
    await state.set_state(Booking.confirm)
    await message.answer(
        t("confirm_title", lang, branch=branch.name, date=data["day"],
          hour=data["hour"], end=data["hour"] + num_hours, hours=num_hours, people=people),
        reply_markup=confirm_kb(lang),
    )


@router.callback_query(Booking.confirm, F.data == "confirm:no")
async def confirm_no(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.message.answer(t("cancelled_flow", lang))
    await cb.answer()


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def confirm_yes(cb: CallbackQuery, state: FSMContext, lang: str, bot: Bot, session_factory):
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        booking = await slots.create_booking(
            session, cb.from_user.id, data["branch_id"], day, data["hour"], data["people"]
        )
        if booking is None:
            # Slot taken between listing and confirm -> re-list times.
            branch = await slots.get_branch(session, data["branch_id"])
            hours = await slots.free_hours(session, branch, day, _now())
            await state.set_state(Booking.time)
            await cb.message.answer(t("slot_taken", lang), reply_markup=times_kb(hours, lang))
            await cb.answer()
            return
        # branch_name is denormalized on the booking; load the user for the DM.
        user = await session.get(User, cb.from_user.id)
    await state.clear()
    await cb.message.answer(
        t("booking_confirmed", lang, branch=booking.branch_name, date=data["day"],
          hour=data["hour"], end=data["hour"] + booking.num_hours, hours=booking.num_hours)
    )
    await notify.notify_new_booking(bot, session_factory, get_settings().admin_ids, booking, user)
    await cb.answer()
