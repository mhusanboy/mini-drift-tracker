from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.locales import t
from bot.services import stats

router = Router()
LANG = "ru"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    async with session_factory() as session:
        ov = await stats.overview(session, date.today())
    by_branch = "\n".join(
        t("stats_branch_line", LANG, name=n, count=c) for n, c in ov["by_branch"]
    ) or "—"
    await message.answer(t(
        "stats_overview", LANG, users=ov["users"], bookings=ov["bookings"],
        today=ov["today"], by_branch=by_branch,
    ))


def _users_page_kb(page: int, pages: int):
    b = InlineKeyboardBuilder()
    if page > 1:
        b.button(text="⬅️", callback_data=f"users:page:{page - 1}")
    if page < pages:
        b.button(text="➡️", callback_data=f"users:page:{page + 1}")
    return b.as_markup()


async def _render_users(target, page: int, session_factory):
    async with session_factory() as session:
        rows, pages = await stats.user_stats_page(session, page)
    header = t("users_header", LANG, page=page, pages=pages)
    cards = "\n\n".join(
        t("user_card", LANG, name=r.name, phone=r.phone, bookings=r.bookings,
          people=r.people, first=r.first_seen, last=r.last_booking or "—",
          fav=r.favorite_branch or "—")
        for r in rows
    ) or "—"
    await target.answer(header + "\n\n" + cards, reply_markup=_users_page_kb(page, pages))


@router.message(Command("users"))
async def cmd_users(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    await _render_users(message, 1, session_factory)


@router.callback_query(F.data.startswith("users:page:"))
async def users_page(cb: CallbackQuery, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    page = int(cb.data.split(":")[2])
    await _render_users(cb.message, page, session_factory)
    await cb.answer()
