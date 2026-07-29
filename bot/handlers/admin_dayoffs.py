from datetime import date, datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from bot.config import get_settings
from bot.handlers.ui import edit_screen
from bot.keyboards.admin import dayoffs_kb
from bot.locales import t
from bot.services import slots

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _dayoffs_markup(session_factory, lang: str):
    today = datetime.now().date()
    days = slots.next_days(today)
    async with session_factory() as session:
        offs = await slots.day_offs_in(session, days)
    return dayoffs_kb(days, offs, today, lang)


@router.callback_query(F.data == "adm:dayoffs")
async def panel_dayoffs(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    markup = await _dayoffs_markup(session_factory, lang)
    await edit_screen(cb, t("dayoffs_title", lang), markup)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:dayoff:"))
async def toggle_dayoff(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    day = date.fromisoformat(cb.data.split(":", 2)[2])
    async with session_factory() as session:
        await slots.toggle_day_off(session, day)
    # Refresh only the toggle grid in place.
    markup = await _dayoffs_markup(session_factory, lang)
    try:
        await cb.message.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest:
        pass
    await cb.answer()
