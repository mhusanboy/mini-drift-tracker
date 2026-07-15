from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import User
from bot.keyboards.booking import my_bookings_kb
from bot.keyboards.common import back_kb
from bot.locales import t
from bot.services import notify, slots

router = Router()


async def _render_bookings(target, user_id: int, lang: str, session_factory) -> None:
    async with session_factory() as session:
        bookings = await slots.upcoming_bookings(session, user_id, datetime.now())
    if not bookings:
        await target.answer(t("my_bookings_empty", lang), reply_markup=back_kb("back:main", lang))
        return
    lines = [
        t("booking_line", lang, date=b.date.isoformat(),
          hour=b.start_hour, end=b.start_hour + b.num_hours, hours=b.num_hours,
          people=b.people_count)
        for b in bookings
    ]
    text = t("my_bookings_title", lang) + "\n\n" + "\n".join(lines)
    await target.answer(text, reply_markup=my_bookings_kb(bookings, lang))


@router.message(Command("mybookings"))
async def cmd_my_bookings(message: Message, lang: str, session_factory):
    await _render_bookings(message, message.from_user.id, lang, session_factory)


@router.callback_query(F.data == "menu:mybookings")
async def menu_my_bookings(cb: CallbackQuery, lang: str, session_factory):
    await _render_bookings(cb.message, cb.from_user.id, lang, session_factory)
    await cb.answer()


@router.callback_query(F.data.startswith("cancelbk:"))
async def cancel_booking(cb: CallbackQuery, lang: str, bot: Bot, session_factory):
    booking_id = int(cb.data.split(":")[1])
    async with session_factory() as session:
        booking = await slots.cancel_booking(session, booking_id, cb.from_user.id)
        user = await session.get(User, cb.from_user.id)
    if booking is None:
        await cb.answer()
        return
    await cb.message.answer(t("booking_cancelled_user", lang))
    await notify.notify_cancellation(bot, session_factory, get_settings().admin_ids, booking, user)
    await cb.answer()
