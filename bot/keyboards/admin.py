from datetime import date

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import day_label, with_back
from bot.locales import t


def admin_panel_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_admin_service", lang), callback_data="adm:service")
    b.button(text=t("btn_admin_bookings", lang), callback_data="adm:bookings")
    b.button(text=t("btn_admin_dayoffs", lang), callback_data="adm:dayoffs")
    b.button(text=t("btn_admin_stats", lang), callback_data="adm:stats")
    b.button(text=t("btn_admin_users", lang), callback_data="adm:users")
    b.button(text=t("btn_admin_export", lang), callback_data="adm:export")
    b.adjust(1)
    return with_back(b.as_markup(), "back:main", lang)


def service_edit_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_edit_service", lang), callback_data="adm:service:edit")
    b.adjust(1)
    return with_back(b.as_markup(), "back:panel", lang)


def admin_days_kb(days: list[date], counts: dict, today: date, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(
            text=f"{day_label(d, today, lang)} ({counts.get(d, 0)})",
            callback_data=f"adm:bday:{d.isoformat()}",
        )
    b.adjust(3)
    return with_back(b.as_markup(), "back:panel", lang)


def dayoffs_kb(days: list[date], offs: set, today: date, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        mark = "🚫" if d in offs else "🟢"
        b.button(text=f"{mark} {day_label(d, today, lang)}", callback_data=f"adm:dayoff:{d.isoformat()}")
    b.adjust(2)
    return with_back(b.as_markup(), "back:panel", lang)
