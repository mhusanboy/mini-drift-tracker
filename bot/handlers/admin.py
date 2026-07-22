"""Admin panel: entry screen, free times, stats, history export, users."""
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import get_settings
from bot.handlers import ui
from bot.keyboards.admin import admin_panel_kb, users_page_kb
from bot.keyboards.common import back_kb, day_label
from bot.locales import LANGUAGES, t
from bot.services import bookings, service, slots, stats, users
from bot.services.export import build_stats_workbook
from bot.timeutil import fmt_minutes

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


# --- Panel ------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message, lang: str):
    await ui.drop(message)
    if not _is_admin(message.from_user.id):
        await ui.send(message, t("not_authorized", lang))
        return
    await ui.show_screen(message, t("admin_panel_title", lang), admin_panel_kb(lang))


@router.callback_query(F.data.in_({"adm:panel", "back:panel"}))
async def panel(cb: CallbackQuery, state: FSMContext, lang: str):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await state.clear()
    await ui.edit_screen(cb, t("admin_panel_title", lang), admin_panel_kb(lang))
    await cb.answer()


# --- Free times -------------------------------------------------------------

def _busy_rows(taken, lang: str) -> list[str]:
    return [
        t("free_busy_row", lang,
          start=fmt_minutes(b.start_minute),
          end=fmt_minutes(b.start_minute + b.duration_hours * 60),
          name=b.full_name, people=b.people_count)
        for b in taken
    ]


def _day_block(day: date, today: date, free: list[int], taken, lang: str) -> str:
    lines = [
        t("free_day", lang, day=day_label(day, today, lang), date=day.strftime("%d.%m")),
        ", ".join(fmt_minutes(m) for m in free) or t("free_none", lang),
    ]
    if taken:
        lines.append(t("free_busy_title", lang))
        lines.extend(_busy_rows(taken, lang))
    return "\n".join(lines)


async def _free_content(session_factory, lang: str):
    now = datetime.now()
    async with session_factory() as session:
        svc = await service.get_service(session)
        if not slots.has_hours(svc):
            return t("free_hours_not_set", lang), back_kb("back:panel", lang)
        blocks = []
        for day in slots.next_days(now.date()):
            taken = await slots.accepted_on(session, day)
            blocks.append(_day_block(
                day, now.date(), slots.free_slots(svc, taken, day, now), taken, lang,
            ))
    return t("free_title", lang) + "\n\n" + "\n\n".join(blocks), back_kb("back:panel", lang)


@router.callback_query(F.data == "adm:free")
async def panel_free(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    text, markup = await _free_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


# --- Stats ------------------------------------------------------------------

async def _stats_content(session_factory, lang: str):
    async with session_factory() as session:
        overview = await stats.overview(session, date.today())
    return t("stats_overview", lang, **overview), back_kb("back:panel", lang)


@router.message(Command("stats"))
async def cmd_stats(message: Message, lang: str, session_factory):
    await ui.drop(message)
    if not _is_admin(message.from_user.id):
        await ui.send(message, t("not_authorized", lang))
        return
    text, markup = await _stats_content(session_factory, lang)
    await ui.show_screen(message, text, markup)


@router.callback_query(F.data == "adm:stats")
async def panel_stats(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    text, markup = await _stats_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


# --- Booking history (Excel) ------------------------------------------------

async def _send_history(target: Message, session_factory, lang: str) -> None:
    today = date.today()
    async with session_factory() as session:
        overview = await stats.overview(session, today)
        customers = await stats.all_user_stats(session)
        history = await bookings.history(session)
    workbook = build_stats_workbook(overview, customers, history, today, lang)
    document = BufferedInputFile(workbook, filename=f"carting-bookings-{today.isoformat()}.xlsx")
    # Deliberately not part of the live screen: the admin asked for this file,
    # so navigating on must not delete it.
    await target.answer_document(document, caption=t("xls_caption", lang, date=today.isoformat()))


@router.message(Command("export"))
async def cmd_export(message: Message, lang: str, session_factory):
    await ui.drop(message)
    if not _is_admin(message.from_user.id):
        await ui.send(message, t("not_authorized", lang))
        return
    await _send_history(message, session_factory, lang)


@router.callback_query(F.data == "adm:history")
async def panel_history(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    await _send_history(cb.message, session_factory, lang)
    await cb.answer()


# --- Users ------------------------------------------------------------------

async def _users_content(page: int, session_factory, lang: str):
    async with session_factory() as session:
        rows, page, pages = await users.users_page(session, page)
        total = await users.count_users(session)
    if not rows:
        return t("users_empty", lang), back_kb("back:panel", lang)
    cards = "\n\n".join(
        t("user_card", lang, name=u.full_name, phone=u.phone,
          language=LANGUAGES.get(u.language, u.language),
          joined=u.created_at.date().isoformat() if u.created_at else "—")
        for u in rows
    )
    header = t("users_header", lang, total=total, page=page, pages=pages)
    return header + "\n\n" + cards, users_page_kb(page, pages, lang)


@router.message(Command("users"))
async def cmd_users(message: Message, lang: str, session_factory):
    await ui.drop(message)
    if not _is_admin(message.from_user.id):
        await ui.send(message, t("not_authorized", lang))
        return
    text, markup = await _users_content(1, session_factory, lang)
    await ui.show_screen(message, text, markup)


@router.callback_query(F.data == "adm:users")
async def panel_users(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    text, markup = await _users_content(1, session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


@router.callback_query(F.data.startswith("users:page:"))
async def users_page(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    page = int(cb.data.split(":")[2])
    text, markup = await _users_content(page, session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()
