from datetime import date, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import get_settings
from bot.handlers.ui import edit_screen
from bot.keyboards.admin import admin_days_kb, day_bookings_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import slots, stats
from bot.timeutil import fmt_minutes

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


def _mark(attended) -> str:
    return "✅" if attended is True else "❌" if attended is False else "🔹"


async def _days_content(session_factory, lang: str):
    now = datetime.now()
    days = slots.next_days(now.date())
    async with session_factory() as session:
        counts = await stats.booking_counts(session, days, now)
    return t("bookings_choose_day", lang), admin_days_kb(days, counts, now.date(), lang)


async def _day_content(day: date, session_factory, lang: str):
    now = datetime.now()
    async with session_factory() as session:
        rows = await stats.bookings_on_day(session, day, now)
    if not rows:
        return t("bookings_day_empty", lang, date=day.isoformat()), back_kb("back:bdays", lang)
    lines = [
        t("booking_admin_line", lang, mark=_mark(r.attended),
          time=fmt_minutes(r.start_minute), end=fmt_minutes(r.start_minute + r.num_hours * 60),
          people=r.people_count, name=r.user_name, phone=r.user_phone)
        for r in rows
    ]
    text = t("bookings_day_title", lang, date=day.isoformat()) + "\n\n" + "\n".join(lines)
    return text, day_bookings_kb(rows, lang)


@router.callback_query(F.data.in_({"adm:bookings", "back:bdays"}))
async def panel_bookings(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    text, markup = await _days_content(session_factory, lang)
    await edit_screen(cb, text, markup)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:bday:"))
async def show_day_bookings(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    day = date.fromisoformat(cb.data.split(":", 2)[2])
    text, markup = await _day_content(day, session_factory, lang)
    await edit_screen(cb, text, markup)
    await cb.answer()


@router.callback_query(F.data.startswith("att:"))
async def mark_attendance(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    _, action, booking_id = cb.data.split(":")
    async with session_factory() as session:
        booking = await slots.set_attended(session, int(booking_id), action == "came")
    if booking is None:
        await cb.answer()
        return
    text, markup = await _day_content(booking.date, session_factory, lang)
    await edit_screen(cb, text, markup)
    await cb.answer()
