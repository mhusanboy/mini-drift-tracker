import logging

from aiogram import Bot

from bot.db.models import User
from bot.locales import t
from bot.timeutil import fmt_minutes

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_LANG = "ru"


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001 - best-effort notification
        logger.warning("Failed to notify admin %s: %s", chat_id, exc)


async def _admin_lang(session_factory, admin_id: int) -> str:
    async with session_factory() as session:
        admin = await session.get(User, admin_id)
    return admin.language if admin else DEFAULT_ADMIN_LANG


def _times(booking):
    start = fmt_minutes(booking.start_minute)
    end = fmt_minutes(booking.start_minute + booking.num_hours * 60)
    return start, end


async def notify_new_booking(bot: Bot, session_factory, admin_ids, booking, user) -> None:
    start, end = _times(booking)
    for admin_id in admin_ids:
        lang = await _admin_lang(session_factory, admin_id)
        text = t(
            "admin_new_booking", lang,
            date=booking.date.isoformat(), time=start, end=end,
            hours=booking.num_hours, people=booking.people_count,
            name=user.full_name, phone=user.phone,
        )
        await _safe_send(bot, admin_id, text)


async def notify_cancellation(bot: Bot, session_factory, admin_ids, booking, user) -> None:
    start, end = _times(booking)
    for admin_id in admin_ids:
        lang = await _admin_lang(session_factory, admin_id)
        text = t(
            "admin_cancelled", lang,
            date=booking.date.isoformat(), time=start, end=end,
            name=user.full_name, phone=user.phone,
        )
        await _safe_send(bot, admin_id, text)
