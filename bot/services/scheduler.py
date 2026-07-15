"""Background scheduler: sends ~1h-before reminders and post-visit rating
requests. Runs as an asyncio task inside the bot process; the "which bookings
are due" logic lives in bot.services.slots (tested there)."""
import asyncio
import logging
from datetime import datetime

from aiogram import Bot

from bot.keyboards.booking import come_kb, rating_kb
from bot.locales import t
from bot.services import slots
from bot.timeutil import fmt_minutes

logger = logging.getLogger(__name__)


def _lang(booking) -> str:
    return booking.user.language if booking.user else "ru"


async def tick(bot: Bot, session_factory, now: datetime | None = None) -> None:
    now = now or datetime.now()

    async with session_factory() as session:
        due_reminders = await slots.due_for_reminder(session, now)
    for b in due_reminders:
        try:
            await bot.send_message(
                b.user_id,
                t("reminder_text", _lang(b), date=b.date.isoformat(),
                  time=fmt_minutes(b.start_minute)),
                reply_markup=come_kb(b.id, _lang(b)),
            )
        except Exception as exc:  # noqa: BLE001 - user may have blocked the bot
            logger.warning("Reminder to %s failed: %s", b.user_id, exc)
        # Mark either way so we don't retry the same booking every minute.
        async with session_factory() as session:
            await slots.mark_reminded(session, b.id)

    async with session_factory() as session:
        due_ratings = await slots.due_for_rating(session, now)
    for b in due_ratings:
        try:
            await bot.send_message(
                b.user_id, t("rating_request", _lang(b)),
                reply_markup=rating_kb(b.id, _lang(b)),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rating request to %s failed: %s", b.user_id, exc)
        async with session_factory() as session:
            await slots.mark_rating_requested(session, b.id)


async def run_scheduler(bot: Bot, session_factory, interval: int = 60) -> None:
    while True:
        try:
            await tick(bot, session_factory)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            logger.exception("Scheduler tick failed: %s", exc)
        await asyncio.sleep(interval)
