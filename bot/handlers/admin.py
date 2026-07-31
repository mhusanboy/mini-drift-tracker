"""Admin panel: entry screen, free times, stats, history export, users."""
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import get_settings
from bot.handlers import ui
from bot.keyboards.admin import admin_panel_kb, free_times_kb, users_page_kb
from bot.keyboards.common import back_kb, day_label
from bot.locales import LANGUAGES, t
from bot.services import bookings, service, slots, stats, users
from bot.services.export import build_stats_workbook
from bot.timeutil import fmt_minutes, now_local, today_local

router = Router()


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


# --- Panel ------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message, lang: str):
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

async def _free_content(session_factory, lang: str):
    now = now_local()
    async with session_factory() as session:
        svc = await service.get_service(session)
        if not slots.has_hours(svc):
            return t("free_hours_not_set", lang), back_kb("back:panel", lang)
        days = []
        for day in slots.next_days(now.date()):
            taken = await slots.accepted_on(session, day)
            days.append({
                "date": day,
                "label": day_label(day, now.date(), lang),
                "slots": slots.day_schedule(svc, taken, day, now),
            })
    return t("free_title", lang) + "\n\n" + t("free_hint", lang), free_times_kb(days, lang)


@router.callback_query(F.data == "adm:free")
async def panel_free(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    text, markup = await _free_content(session_factory, lang)
    await ui.edit_screen(cb, text, markup)
    await cb.answer()


@router.callback_query(F.data == "free:noop")
async def free_noop(cb: CallbackQuery):
    # The per-day header is a label, not an action.
    await cb.answer()


@router.callback_query(F.data.startswith("free:slot:"))
async def free_slot(cb: CallbackQuery, lang: str, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer(t("not_authorized", lang), show_alert=True)
        return
    _, _, iso, minute = cb.data.split(":")
    day = date.fromisoformat(iso)
    async with session_factory() as session:
        taken = await slots.accepted_on(session, day)
    booking = slots.covered_by(taken, int(minute))
    if booking is None:
        await cb.answer(t("free_slot_free_toast", lang))
        return
    end = booking.start_minute + booking.duration_hours * 60
    await cb.answer(
        t("free_slot_detail", lang, time=fmt_minutes(booking.start_minute),
          end=fmt_minutes(end), name=booking.full_name, people=booking.people_count),
        show_alert=True,
    )


# --- Stats ------------------------------------------------------------------

async def _stats_content(session_factory, lang: str):
    async with session_factory() as session:
        overview = await stats.overview(session, today_local())
    return t("stats_overview", lang, **overview), back_kb("back:panel", lang)


@router.message(Command("stats"))
async def cmd_stats(message: Message, lang: str, session_factory):
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
    today = today_local()
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
