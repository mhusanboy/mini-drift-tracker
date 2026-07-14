from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def admin_panel_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_admin_branches", lang), callback_data="adm:branches")
    b.button(text=t("btn_admin_stats", lang), callback_data="adm:stats")
    b.button(text=t("btn_admin_users", lang), callback_data="adm:users")
    b.adjust(1)
    return b.as_markup()


def admin_branches_kb(branches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=t("btn_edit", lang, name=br.name), callback_data=f"abranch:edit:{br.id}")
        b.button(text=t("btn_toggle_active", lang), callback_data=f"abranch:toggle:{br.id}")
    b.button(text=t("btn_add_branch", lang), callback_data="abranch:add")
    b.adjust(2)
    return b.as_markup()
