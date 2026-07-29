from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import LANGUAGES, t


def back_button(target: str, lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("back", lang), callback_data=target)


def back_kb(target: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button(target, lang)]])


def with_back(markup: InlineKeyboardMarkup, target: str, lang: str) -> InlineKeyboardMarkup:
    """Append a Back button row to an existing inline keyboard."""
    markup.inline_keyboard.append([back_button(target, lang)])
    return markup


def language_kb(lang: str = "ru", back: str | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, label in LANGUAGES.items():
        b.button(text=label, callback_data=f"lang:{code}")
    b.adjust(1)
    markup = b.as_markup()
    if back:
        with_back(markup, back, lang)
    return markup


def main_menu_kb(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_book", lang), callback_data="menu:book")
    b.button(text=t("btn_my_bookings", lang), callback_data="menu:mybookings")
    b.button(text=t("btn_language", lang), callback_data="menu:language")
    if is_admin:
        b.button(text=t("btn_admin", lang), callback_data="adm:panel")
    b.adjust(1)
    return b.as_markup()


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("share_phone_button", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def day_label(d: date, today: date, lang: str) -> str:
    if d == today:
        return t("today", lang)
    if (d - today).days == 1:
        return t("tomorrow", lang)
    return d.strftime("%d.%m")
