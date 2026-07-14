from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def admin_branches_kb(branches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=t("btn_edit", lang, name=br.name), callback_data=f"abranch:edit:{br.id}")
        b.button(text=t("btn_toggle_active", lang), callback_data=f"abranch:toggle:{br.id}")
    b.button(text=t("btn_add_branch", lang), callback_data="abranch:add")
    b.adjust(2)
    return b.as_markup()
