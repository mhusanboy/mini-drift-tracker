import logging

from aiogram import Bot

from bot.db.models import User
from bot.locales import t

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_LANG = "ru"


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001 - best-effort notification
        logger.warning("Failed to notify admin %s: %s", chat_id, exc)


async def _admin_lang(session_factory, admin_id: int) -> str:
    """The admin's chosen language, or Russian if they haven't registered."""
    async with session_factory() as session:
        admin = await session.get(User, admin_id)
    return admin.language if admin else DEFAULT_ADMIN_LANG


async def notify_new_booking(bot: Bot, session_factory, admin_ids, booking, user) -> None:
    for admin_id in admin_ids:
        lang = await _admin_lang(session_factory, admin_id)
        text = t(
            "admin_new_booking", lang,
            branch=booking.branch.name, date=booking.date.isoformat(),
            hour=booking.start_hour, end=booking.start_hour + booking.num_hours,
            hours=booking.num_hours, people=booking.people_count,
            name=user.full_name, phone=user.phone,
        )
        await _safe_send(bot, admin_id, text)


async def notify_cancellation(bot: Bot, session_factory, admin_ids, booking, user) -> None:
    for admin_id in admin_ids:
        lang = await _admin_lang(session_factory, admin_id)
        text = t(
            "admin_cancelled", lang,
            branch=booking.branch.name, date=booking.date.isoformat(),
            hour=booking.start_hour, end=booking.start_hour + booking.num_hours,
            name=user.full_name, phone=user.phone,
        )
        await _safe_send(bot, admin_id, text)
