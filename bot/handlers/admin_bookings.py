from datetime import date, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.admin import admin_days_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import slots, stats

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_days(target, session_factory, lang: str) -> None:
    today = datetime.now().date()
    days = slots.next_days(today)
    async with session_factory() as session:
        counts = await stats.booking_counts(session, days)
    await target.answer(t("bookings_choose_day", lang),
                        reply_markup=admin_days_kb(days, counts, today, lang))


@router.callback_query(F.data.in_({"adm:bookings", "back:bdays"}))
async def panel_bookings(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _render_days(cb.message, session_factory, lang)
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
        await cb.message.answer(t("bookings_day_empty", lang, date=day.isoformat()),
                                reply_markup=back_kb("back:bdays", lang))
        await cb.answer()
        return
    lines = [
        t("booking_admin_line", lang, hour=r.start_hour, end=r.start_hour + r.num_hours,
          people=r.people_count, name=r.user_name, phone=r.user_phone)
        for r in rows
    ]
    await cb.message.answer(
        t("bookings_day_title", lang, date=day.isoformat()) + "\n\n" + "\n".join(lines),
        reply_markup=back_kb("back:bdays", lang),
    )
    await cb.answer()
