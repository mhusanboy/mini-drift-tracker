"""Callbacks for the pre-booking reminder and the post-visit rating."""
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from bot.config import get_settings
from bot.db.models import User
from bot.handlers.ui import edit_screen
from bot.locales import t
from bot.services import notify, slots

router = Router()


@router.callback_query(F.data.startswith("come:yes:"))
async def come_yes(cb: CallbackQuery, lang: str):
    await edit_screen(cb, t("reminder_yes_ack", lang))
    await cb.answer()


@router.callback_query(F.data.startswith("come:no:"))
async def come_no(cb: CallbackQuery, lang: str, bot: Bot, session_factory):
    booking_id = int(cb.data.split(":")[2])
    async with session_factory() as session:
        booking = await slots.cancel_booking(session, booking_id, cb.from_user.id)
        user = await session.get(User, cb.from_user.id)
    await edit_screen(cb, t("reminder_cancelled", lang))
    await cb.answer()
    if booking is not None:
        await notify.notify_cancellation(bot, session_factory, get_settings().admin_ids, booking, user)


@router.callback_query(F.data.startswith("rate:"))
async def rate(cb: CallbackQuery, lang: str, session_factory):
    _, booking_id, value = cb.data.split(":")
    async with session_factory() as session:
        await slots.set_rating(session, int(booking_id), cb.from_user.id, int(value))
    await edit_screen(cb, t("rating_thanks", lang))
    await cb.answer()
