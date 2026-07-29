from datetime import date

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import day_label, with_back
from bot.locales import t
from bot.timeutil import fmt_minutes


def days_kb(days: list[date], today: date, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(text=day_label(d, today, lang), callback_data=f"day:{d.isoformat()}")
    b.adjust(2)
    return with_back(b.as_markup(), "back:main", lang)


def slots_kb(slots_min: list[int], lang: str) -> InlineKeyboardMarkup:
    """Free start times in chronological order, two per row (e.g.
    16:30 | 17:00 / 17:30 | 18:00). Whether a row starts on :00 or :30 just
    depends on which slots are free."""
    b = InlineKeyboardBuilder()
    for m in sorted(slots_min):
        b.button(text=fmt_minutes(m), callback_data=f"slot:{m}")
    b.adjust(2)
    return with_back(b.as_markup(), "back:days", lang)


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_confirm", lang), callback_data="confirm:yes")
    b.button(text=t("back", lang), callback_data="back:times")
    b.adjust(1)
    return b.as_markup()


def my_bookings_kb(bookings, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.button(
            text=t("btn_cancel_booking", lang, date=bk.date.strftime("%d.%m"),
                   time=fmt_minutes(bk.start_minute)),
            callback_data=f"cancelbk:{bk.id}",
        )
    b.adjust(1)
    return with_back(b.as_markup(), "back:main", lang)


def come_kb(booking_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_come_yes", lang), callback_data=f"come:yes:{booking_id}")
    b.button(text=t("btn_come_no", lang), callback_data=f"come:no:{booking_id}")
    b.adjust(1)
    return b.as_markup()


def rating_kb(booking_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in range(1, 6):
        b.button(text=f"{n}⭐", callback_data=f"rate:{booking_id}:{n}")
    b.adjust(5)
    return b.as_markup()
