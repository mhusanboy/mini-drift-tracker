from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import LANGUAGES, t


def day_label(day: date, today: date, lang: str) -> str:
    if day == today:
        return t("today", lang)
    if (day - today).days == 1:
        return t("tomorrow", lang)
    return day.strftime("%d.%m")


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
    b.button(text=t("btn_location", lang), callback_data="menu:location")
    b.button(text=t("btn_prices", lang), callback_data="menu:prices")
    b.button(text=t("btn_promos", lang), callback_data="menu:promos")
    b.button(text=t("btn_book", lang), callback_data="menu:book")
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


def booking_link_kb(url: str, lang: str) -> InlineKeyboardMarkup:
    """The deep link into the admin's DM, plus a way back to the menu."""
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_open_dm", lang), url=url)]]
    )
    return with_back(markup, "back:main", lang)
