"""The booking-request card sent to admins.

The card is a standalone record, not part of the customer's or the admin's live
screen: it is sent directly and edited in place as the admin decides or edits.
Each admin gets their own copy; a copy re-renders from the database whenever
that admin touches it, so a copy another admin has already acted on catches up
on their next tap.
"""
import logging

from aiogram import Bot

from bot.db.models import BookingStatus, User
from bot.locales import t
from bot.timeutil import fmt_minutes

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_LANG = "ru"

_STATUS_KEY = {
    BookingStatus.PENDING: "status_pending",
    BookingStatus.ACCEPTED: "status_accepted",
    BookingStatus.REJECTED: "status_rejected",
}


async def admin_lang(session_factory, admin_id: int) -> str:
    async with session_factory() as session:
        admin = await session.get(User, admin_id)
    return admin.language if admin else DEFAULT_ADMIN_LANG


def when_line(booking, lang: str) -> str:
    """The resolved slot, with the customer's own words alongside it — so a
    misread is visible rather than silently wrong."""
    if booking.date is None or booking.start_minute is None:
        return t("card_when_unknown", lang, text=booking.when_text)
    end = booking.start_minute + booking.duration_hours * 60
    return t(
        "card_when", lang,
        date=booking.date.strftime("%d.%m"),
        time=fmt_minutes(booking.start_minute),
        end=fmt_minutes(end),
        text=booking.when_text,
    )


def card_text(booking, lang: str) -> str:
    return t(
        "card", lang,
        status=t(_STATUS_KEY[booking.status], lang),
        name=booking.full_name,
        phone=booking.phone,
        when=when_line(booking, lang),
        people=booking.people_count,
        hours=booking.duration_hours,
    )


async def send_request(bot: Bot, session_factory, admin_ids, booking) -> None:
    from bot.keyboards.booking import card_kb  # circular at import time

    for admin_id in admin_ids:
        lang = await admin_lang(session_factory, admin_id)
        try:
            await bot.send_message(
                admin_id, card_text(booking, lang),
                reply_markup=card_kb(booking, lang),
            )
        except Exception as exc:  # noqa: BLE001 - admin may not have opened the bot
            logger.warning("Could not send request %s to %s: %s", booking.id, admin_id, exc)
