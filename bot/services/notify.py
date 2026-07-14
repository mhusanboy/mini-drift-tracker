import logging

from aiogram import Bot

from bot.locales import t

logger = logging.getLogger(__name__)

ADMIN_LANG = "ru"


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001 - best-effort notification
        logger.warning("Failed to notify admin %s: %s", chat_id, exc)


async def notify_new_booking(bot: Bot, admin_ids, booking, user) -> None:
    text = t(
        "admin_new_booking", ADMIN_LANG,
        branch=booking.branch.name, date=booking.date.isoformat(),
        hour=booking.start_hour, people=booking.people_count,
        name=user.full_name, phone=user.phone,
    )
    for admin_id in admin_ids:
        await _safe_send(bot, admin_id, text)


async def notify_cancellation(bot: Bot, admin_ids, booking, user) -> None:
    text = t(
        "admin_cancelled", ADMIN_LANG,
        branch=booking.branch.name, date=booking.date.isoformat(),
        hour=booking.start_hour, name=user.full_name, phone=user.phone,
    )
    for admin_id in admin_ids:
        await _safe_send(bot, admin_id, text)
