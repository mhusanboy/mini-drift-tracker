from datetime import date, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.admin import dayoffs_kb
from bot.locales import t
from bot.services import slots

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_dayoffs(target, session_factory, lang: str, edit: bool = False) -> None:
    today = datetime.now().date()
    days = slots.next_days(today)
    async with session_factory() as session:
        offs = await slots.day_offs_in(session, days)
    markup = dayoffs_kb(days, offs, today, lang)
    if edit:
        await target.edit_reply_markup(reply_markup=markup)
    else:
        await target.answer(t("dayoffs_title", lang), reply_markup=markup)


@router.callback_query(F.data == "adm:dayoffs")
async def panel_dayoffs(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _render_dayoffs(cb.message, session_factory, lang)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:dayoff:"))
async def toggle_dayoff(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    day = date.fromisoformat(cb.data.split(":", 2)[2])
    async with session_factory() as session:
        await slots.toggle_day_off(session, day)
    # Refresh the toggle grid in place.
    await _render_dayoffs(cb.message, session_factory, lang, edit=True)
    await cb.answer()
