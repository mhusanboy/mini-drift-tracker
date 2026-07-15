from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import back_button, day_label, with_back
from bot.locales import t
from bot.timeutil import fmt_minutes


def days_kb(days: list[date], today: date, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(text=day_label(d, today, lang), callback_data=f"day:{d.isoformat()}")
    b.adjust(2)
    return with_back(b.as_markup(), "back:main", lang)


def slots_kb(slots_min: list[int], lang: str) -> InlineKeyboardMarkup:
    """Two columns: on-the-hour (:00) starts on the left, half-hour (:30) on the
    right, zipped row by row (e.g. 11:00 | 11:30)."""
    b = InlineKeyboardBuilder()
    on_hour = [m for m in slots_min if m % 60 == 0]
    half = [m for m in slots_min if m % 60 == 30]
    for i in range(max(len(on_hour), len(half))):
        row = []
        if i < len(on_hour):
            row.append(InlineKeyboardButton(text=fmt_minutes(on_hour[i]),
                                            callback_data=f"slot:{on_hour[i]}"))
        if i < len(half):
            row.append(InlineKeyboardButton(text=fmt_minutes(half[i]),
                                            callback_data=f"slot:{half[i]}"))
        b.row(*row)
    b.row(back_button("back:days", lang))
    return b.as_markup()


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
