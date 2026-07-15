from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.keyboards.admin import admin_panel_kb
from bot.locales import t
from bot.services import stats
from bot.services.export import build_stats_workbook

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _show_panel(target, lang: str) -> None:
    await target.answer(t("admin_panel_title", lang), reply_markup=admin_panel_kb(lang))


@router.message(Command("admin"))
async def cmd_admin(message: Message, lang: str):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _show_panel(message, lang)


@router.callback_query(F.data == "adm:panel")
async def panel(cb: CallbackQuery, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _show_panel(cb.message, lang)
    await cb.answer()


async def _send_stats(target, session_factory, lang: str) -> None:
    async with session_factory() as session:
        ov = await stats.overview(session, date.today())
    await target.answer(t(
        "stats_overview", lang, users=ov["users"], bookings=ov["bookings"],
        today=ov["today"], people=ov["people"], hours=ov["hours"],
    ))


@router.message(Command("stats"))
async def cmd_stats(message: Message, lang: str, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _send_stats(message, session_factory, lang)


@router.callback_query(F.data == "adm:stats")
async def panel_stats(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _send_stats(cb.message, session_factory, lang)
    await cb.answer()


def _users_page_kb(page: int, pages: int):
    b = InlineKeyboardBuilder()
    if page > 1:
        b.button(text="⬅️", callback_data=f"users:page:{page - 1}")
    if page < pages:
        b.button(text="➡️", callback_data=f"users:page:{page + 1}")
    return b.as_markup()


async def _render_users(target, page: int, session_factory, lang: str):
    async with session_factory() as session:
        rows, pages = await stats.user_stats_page(session, page)
    header = t("users_header", lang, page=page, pages=pages)
    cards = "\n\n".join(
        t("user_card", lang, name=r.name, phone=r.phone, bookings=r.bookings,
          people=r.people, first=r.first_seen, last=r.last_booking or "—")
        for r in rows
    ) or "—"
    await target.answer(header + "\n\n" + cards, reply_markup=_users_page_kb(page, pages))


@router.message(Command("users"))
async def cmd_users(message: Message, lang: str, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _render_users(message, 1, session_factory, lang)


@router.callback_query(F.data == "adm:users")
async def panel_users(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _render_users(cb.message, 1, session_factory, lang)
    await cb.answer()


@router.callback_query(F.data.startswith("users:page:"))
async def users_page(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    page = int(cb.data.split(":")[2])
    await _render_users(cb.message, page, session_factory, lang)
    await cb.answer()


async def _send_export(target, session_factory, lang: str) -> None:
    today = date.today()
    async with session_factory() as session:
        overview = await stats.overview(session, today)
        users = await stats.all_user_stats(session)
        bookings = await stats.all_bookings(session)
    data = build_stats_workbook(overview, users, bookings, today, lang)
    document = BufferedInputFile(data, filename=f"carting-stats-{today.isoformat()}.xlsx")
    await target.answer_document(document, caption=t("xls_caption", lang, date=today.isoformat()))


@router.message(Command("export"))
async def cmd_export(message: Message, lang: str, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", lang))
        return
    await _send_export(message, session_factory, lang)


@router.callback_query(F.data == "adm:export")
async def panel_export(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _send_export(cb.message, session_factory, lang)
    await cb.answer()
