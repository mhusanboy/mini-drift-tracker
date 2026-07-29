"""The "Bron qilish" deep link.

The bot records the request itself and notifies the admin, but the customer also
gets a t.me link that opens the admin's DM with the request already typed, so
the two can settle the details there. Format:
``https://t.me/<username>?text=<urlencoded message>``.
"""
from urllib.parse import quote

from bot.locales import t

# Telegram silently drops a ?text= payload that is too long, which would look
# like the button is broken. Keep the free-text part short enough to fit.
MAX_WHEN_LEN = 200


def build_message(lang: str, full_name: str, phone: str, when: str, people: int) -> str:
    return t("booking_dm_template", lang, name=full_name, when=when,
             phone=phone, people=people)


def build_link(username: str, message: str) -> str:
    return f"https://t.me/{username}?text={quote(message, safe='')}"


def build(
    lang: str, username: str, full_name: str, phone: str, when: str, people: int
) -> tuple[str, str]:
    """Return the (message, link) pair for a booking request."""
    message = build_message(lang, full_name, phone, when, people)
    return message, build_link(username, message)
