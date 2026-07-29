"""Build a multi-sheet Excel workbook of the service's statistics.

The builder is a pure, synchronous function over already-fetched data so it is
easy to test (open the bytes with openpyxl and assert) and does not touch the
DB or the event loop's I/O.
"""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from bot.locales import t
from bot.services.stats import BookingRow, UserStat
from bot.timeutil import fmt_minutes

_BOLD = Font(bold=True)


def _autosize(ws) -> None:
    for col_cells in ws.columns:
        width = max((len(str(c.value)) for c in col_cells if c.value is not None), default=0)
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(width + 2, 60)


def _write_header(ws, row: int, headers: list[str]) -> None:
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=title)
        cell.font = _BOLD


def _overview_sheet(ws, overview: dict, today: date, lang: str) -> None:
    ws.title = t("xls_sheet_overview", lang)
    title = ws.cell(row=1, column=1, value=t("xls_title", lang, date=today.isoformat()))
    title.font = Font(bold=True, size=14)
    metrics = [
        (t("xls_metric_users", lang), overview["users"]),
        (t("xls_metric_bookings", lang), overview["bookings"]),
        (t("xls_metric_today", lang), overview["today"]),
        (t("xls_metric_people", lang), overview["people"]),
        (t("xls_metric_hours", lang), overview["hours"]),
    ]
    row = 3
    for label, value in metrics:
        ws.cell(row=row, column=1, value=label).font = _BOLD
        ws.cell(row=row, column=2, value=value)
        row += 1
    _autosize(ws)


def _customers_sheet(ws, users: list[UserStat], lang: str) -> None:
    headers = [
        t("xls_h_name", lang), t("xls_h_phone", lang), t("xls_h_language", lang),
        t("xls_h_bookings", lang), t("xls_h_people", lang), t("xls_h_first", lang),
        t("xls_h_last", lang),
    ]
    _write_header(ws, 1, headers)
    for i, u in enumerate(users, start=2):
        ws.cell(row=i, column=1, value=u.name)
        ws.cell(row=i, column=2, value=u.phone)
        ws.cell(row=i, column=3, value=u.language)
        ws.cell(row=i, column=4, value=u.bookings)
        ws.cell(row=i, column=5, value=u.people)
        ws.cell(row=i, column=6, value=u.first_seen.isoformat() if u.first_seen else "—")
        ws.cell(row=i, column=7, value=u.last_booking.isoformat() if u.last_booking else "—")
    _autosize(ws)


def _bookings_sheet(ws, bookings: list[BookingRow], lang: str) -> None:
    headers = [
        t("xls_h_date", lang), t("xls_h_start", lang), t("xls_h_end", lang),
        t("xls_h_hours", lang), t("xls_h_people", lang),
        t("xls_h_customer", lang), t("xls_h_phone", lang), t("xls_h_status", lang),
        t("xls_h_created", lang),
    ]
    _write_header(ws, 1, headers)
    for i, b in enumerate(bookings, start=2):
        ws.cell(row=i, column=1, value=b.date.isoformat())
        ws.cell(row=i, column=2, value=fmt_minutes(b.start_minute))
        ws.cell(row=i, column=3, value=fmt_minutes(b.start_minute + b.num_hours * 60))
        ws.cell(row=i, column=4, value=b.num_hours)
        ws.cell(row=i, column=5, value=b.people_count)
        ws.cell(row=i, column=6, value=b.user_name)
        ws.cell(row=i, column=7, value=b.user_phone)
        ws.cell(row=i, column=8, value=b.status)
        ws.cell(row=i, column=9, value=b.created_at.isoformat(sep=" ", timespec="minutes") if b.created_at else "—")
    _autosize(ws)


def build_stats_workbook(
    overview: dict,
    users: list[UserStat],
    bookings: list[BookingRow],
    today: date,
    lang: str,
) -> bytes:
    wb = Workbook()
    _overview_sheet(wb.active, overview, today, lang)
    _customers_sheet(wb.create_sheet(t("xls_sheet_customers", lang)), users, lang)
    _bookings_sheet(wb.create_sheet(t("xls_sheet_bookings", lang)), bookings, lang)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
