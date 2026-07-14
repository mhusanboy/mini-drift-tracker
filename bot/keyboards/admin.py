from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def admin_panel_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_admin_branches", lang), callback_data="adm:branches")
    b.button(text=t("btn_admin_stats", lang), callback_data="adm:stats")
    b.button(text=t("btn_admin_users", lang), callback_data="adm:users")
    b.button(text=t("btn_admin_export", lang), callback_data="adm:export")
    b.adjust(1)
    return b.as_markup()


def admin_branches_kb(branches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=t("btn_edit", lang, name=br.name), callback_data=f"abranch:edit:{br.id}")
        b.button(text=t("btn_toggle_active", lang), callback_data=f"abranch:toggle:{br.id}")
        b.button(text=t("btn_delete", lang), callback_data=f"abranch:delete:{br.id}")
    b.button(text=t("btn_add_branch", lang), callback_data="abranch:add")
    b.adjust(3)
    return b.as_markup()


def confirm_delete_branch_kb(branch_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_confirm_delete", lang), callback_data=f"abranch:delyes:{branch_id}")
    b.button(text=t("btn_cancel", lang), callback_data="abranch:delno")
    b.adjust(2)
    return b.as_markup()
