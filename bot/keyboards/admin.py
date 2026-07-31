from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import back_button, with_back
from bot.locales import t
from bot.timeutil import fmt_minutes

# Promo text is free-form and can be long; a button label cannot be.
PROMO_LABEL_LEN = 28


def free_times_kb(days, lang: str) -> InlineKeyboardMarkup:
    """All start times for each day as a 2-column grid. Busy slots carry a ❌ and
    open the booking's details on tap; a per-day header labels each block.

    ``days`` is a list of ``{"date": date, "label": str, "slots": [(minute, busy)]}``.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for d in days:
        rows.append([InlineKeyboardButton(
            text=t("free_day", lang, day=d["label"], date=d["date"].strftime("%d.%m")),
            callback_data="free:noop",
        )])
        pair: list[InlineKeyboardButton] = []
        for minute, busy in d["slots"]:
            pair.append(InlineKeyboardButton(
                text=fmt_minutes(minute) + (" ❌" if busy else ""),
                callback_data=f"free:slot:{d['date'].isoformat()}:{minute}",
            ))
            if len(pair) == 2:
                rows.append(pair)
                pair = []
        if pair:
            rows.append(pair)
    rows.append([back_button("back:panel", lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_admin_settings", lang), callback_data="adm:settings")
    b.button(text=t("btn_admin_free", lang), callback_data="adm:free")
    b.button(text=t("btn_admin_stats", lang), callback_data="adm:stats")
    b.button(text=t("btn_admin_history", lang), callback_data="adm:history")
    b.button(text=t("btn_admin_users", lang), callback_data="adm:users")
    b.adjust(1)
    return with_back(b.as_markup(), "back:main", lang)


def settings_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_edit_price", lang), callback_data="adm:price")
    b.button(text=t("btn_edit_hours", lang), callback_data="adm:hours")
    b.button(text=t("btn_edit_location", lang), callback_data="adm:location")
    b.button(text=t("btn_edit_promos", lang), callback_data="adm:promos")
    b.button(text=t("btn_edit_username", lang), callback_data="adm:username")
    b.adjust(1)
    return with_back(b.as_markup(), "back:panel", lang)


def promo_label(text: str) -> str:
    """First line of the promo, clipped to fit on a button."""
    first = text.strip().splitlines()[0] if text.strip() else "—"
    if len(first) > PROMO_LABEL_LEN:
        first = first[: PROMO_LABEL_LEN - 1].rstrip() + "…"
    return first


def promos_admin_kb(promos, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in promos:
        b.button(
            text=t("btn_del_promo", lang, text=promo_label(p.text)),
            callback_data=f"promo:del:{p.id}",
        )
    b.button(text=t("btn_add_promo", lang), callback_data="promo:add")
    b.adjust(1)
    return with_back(b.as_markup(), "back:settings", lang)


def users_page_kb(page: int, pages: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if page > 1:
        b.button(text="⬅️", callback_data=f"users:page:{page - 1}")
    if page < pages:
        b.button(text="➡️", callback_data=f"users:page:{page + 1}")
    return with_back(b.as_markup(), "back:panel", lang)
