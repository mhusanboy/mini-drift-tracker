from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import LANGUAGES, t


def language_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, label in LANGUAGES.items():
        b.button(text=label, callback_data=f"lang:{code}")
    b.adjust(1)
    return b.as_markup()


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_book", lang), callback_data="menu:book")
    b.button(text=t("btn_my_bookings", lang), callback_data="menu:mybookings")
    b.button(text=t("btn_language", lang), callback_data="menu:language")
    b.adjust(1)
    return b.as_markup()


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("share_phone_button", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
