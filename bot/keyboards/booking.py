"""Keyboards for the admin's booking-request card."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import BookingStatus
from bot.locales import t


def card_kb(booking, lang: str) -> InlineKeyboardMarkup:
    """Accept / Reject / Edit. The decision already taken is marked, and stays
    tappable so it can be changed."""
    b = InlineKeyboardBuilder()
    accepted = "🔸 " if booking.status == BookingStatus.ACCEPTED else ""
    rejected = "🔸 " if booking.status == BookingStatus.REJECTED else ""
    b.button(text=accepted + t("btn_card_accept", lang), callback_data=f"bk:accept:{booking.id}")
    b.button(text=rejected + t("btn_card_reject", lang), callback_data=f"bk:reject:{booking.id}")
    b.button(text=t("btn_card_edit", lang), callback_data=f"bk:edit:{booking.id}")
    b.adjust(2, 1)
    return b.as_markup()


def card_edit_kb(booking, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_card_edit_time", lang), callback_data=f"bk:set:time:{booking.id}")
    b.button(text=t("btn_card_edit_duration", lang), callback_data=f"bk:set:dur:{booking.id}")
    b.button(text=t("btn_card_edit_people", lang), callback_data=f"bk:set:people:{booking.id}")
    b.button(text=t("back", lang), callback_data=f"bk:card:{booking.id}")
    b.adjust(1)
    return b.as_markup()


def card_back_kb(booking_id: int, lang: str) -> InlineKeyboardMarkup:
    """Sole way out of a prompt that is waiting for typed input."""
    b = InlineKeyboardBuilder()
    b.button(text=t("back", lang), callback_data=f"bk:card:{booking_id}")
    return b.as_markup()


def card_conflict_kb(booking_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_conflict_yes", lang), callback_data=f"bk:force:{booking_id}")
    b.button(text=t("back", lang), callback_data=f"bk:card:{booking_id}")
    b.adjust(1)
    return b.as_markup()
