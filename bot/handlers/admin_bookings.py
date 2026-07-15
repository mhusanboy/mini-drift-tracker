from datetime import date, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import get_settings
from bot.handlers.ui import edit_screen
from bot.keyboards.admin import admin_days_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import slots, stats

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _days_content(session_factory, lang: str):
    today = datetime.now().date()
    days = slots.next_days(today)
    async with session_factory() as session:
        counts = await stats.booking_counts(session, days)
    return t("bookings_choose_day", lang), admin_days_kb(days, counts, today, lang)


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
    async with session_factory() as session:
        rows = await stats.bookings_on_day(session, day)
    if not rows:
        await edit_screen(cb, t("bookings_day_empty", lang, date=day.isoformat()),
                          back_kb("back:bdays", lang))
        await cb.answer()
        return
    lines = [
        t("booking_admin_line", lang, hour=r.start_hour, end=r.start_hour + r.num_hours,
          people=r.people_count, name=r.user_name, phone=r.user_phone)
        for r in rows
    ]
    await edit_screen(cb, t("bookings_day_title", lang, date=day.isoformat()) + "\n\n" + "\n".join(lines),
                      back_kb("back:bdays", lang))
    await cb.answer()
