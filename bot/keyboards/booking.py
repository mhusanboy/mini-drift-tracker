from datetime import date

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import day_label
from bot.locales import t


def days_kb(days: list[date], today: date, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(text=day_label(d, today, lang), callback_data=f"day:{d.isoformat()}")
    b.adjust(3)
    return b.as_markup()


def times_kb(hours: list[int], lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for h in hours:
        b.button(text=f"{h:02d}:00", callback_data=f"time:{h}")
    b.adjust(4)
    return b.as_markup()


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_confirm", lang), callback_data="confirm:yes")
    b.button(text=t("btn_cancel", lang), callback_data="confirm:no")
    b.adjust(2)
    return b.as_markup()


def my_bookings_kb(bookings, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.button(
            text=t("btn_cancel_booking", lang, date=bk.date.strftime("%d.%m"), hour=bk.start_hour),
            callback_data=f"cancelbk:{bk.id}",
        )
    b.adjust(1)
    return b.as_markup()
