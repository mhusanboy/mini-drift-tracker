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

from bot.db.models import BookingStatus
from bot.locales import t
from bot.services.stats import BookingRow, UserStat

_BOLD = Font(bold=True)


def _autosize(ws) -> None:
    for col_cells in ws.columns:
        width = max((len(str(c.value)) for c in col_cells if c.value is not None), default=0)
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(width + 2, 60)


def _write_header(ws, row: int, headers: list[str]) -> None:
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=title)
        cell.font = _BOLD


def _overview_sheet(ws, overview: dict, bookings: list[BookingRow], today: date, lang: str) -> None:
    ws.title = t("xls_sheet_overview", lang)
    confirmed = [b for b in bookings if b.status == BookingStatus.CONFIRMED]
    total_people = sum(b.people_count for b in confirmed)
    total_hours = sum(b.num_hours for b in confirmed)

    title = ws.cell(row=1, column=1, value=t("xls_title", lang, date=today.isoformat()))
    title.font = Font(bold=True, size=14)

    metrics = [
        (t("xls_metric_users", lang), overview["users"]),
        (t("xls_metric_bookings", lang), overview["bookings"]),
        (t("xls_metric_today", lang), overview["today"]),
        (t("xls_metric_people", lang), total_people),
        (t("xls_metric_hours", lang), total_hours),
    ]
    row = 3
    for label, value in metrics:
        ws.cell(row=row, column=1, value=label).font = _BOLD
        ws.cell(row=row, column=2, value=value)
        row += 1

    # Per-branch breakdown (confirmed bookings only).
    row += 1
    ws.cell(row=row, column=1, value=t("xls_section_branches", lang)).font = _BOLD
    row += 1
    _write_header(ws, row, [
        t("xls_h_branch", lang), t("xls_h_bookings", lang),
        t("xls_h_people", lang), t("xls_h_hours", lang),
    ])
    row += 1
    agg: dict[str, list[int]] = {}
    for b in confirmed:
        entry = agg.setdefault(b.branch_name, [0, 0, 0])
        entry[0] += 1
        entry[1] += b.people_count
        entry[2] += b.num_hours
    for name in sorted(agg):
        count, people, hours = agg[name]
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=count)
        ws.cell(row=row, column=3, value=people)
        ws.cell(row=row, column=4, value=hours)
        row += 1
    _autosize(ws)


def _customers_sheet(ws, users: list[UserStat], lang: str) -> None:
    headers = [
        t("xls_h_name", lang), t("xls_h_phone", lang), t("xls_h_language", lang),
        t("xls_h_bookings", lang), t("xls_h_people", lang), t("xls_h_first", lang),
        t("xls_h_last", lang), t("xls_h_fav", lang),
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
        ws.cell(row=i, column=8, value=u.favorite_branch or "—")
    _autosize(ws)


def _bookings_sheet(ws, bookings: list[BookingRow], lang: str) -> None:
    headers = [
        t("xls_h_date", lang), t("xls_h_start", lang), t("xls_h_end", lang),
        t("xls_h_hours", lang), t("xls_h_people", lang), t("xls_h_branch", lang),
        t("xls_h_customer", lang), t("xls_h_phone", lang), t("xls_h_status", lang),
        t("xls_h_created", lang),
    ]
    _write_header(ws, 1, headers)
    for i, b in enumerate(bookings, start=2):
        ws.cell(row=i, column=1, value=b.date.isoformat())
        ws.cell(row=i, column=2, value=f"{b.start_hour:02d}:00")
        ws.cell(row=i, column=3, value=f"{b.start_hour + b.num_hours:02d}:00")
        ws.cell(row=i, column=4, value=b.num_hours)
        ws.cell(row=i, column=5, value=b.people_count)
        ws.cell(row=i, column=6, value=b.branch_name)
        ws.cell(row=i, column=7, value=b.user_name)
        ws.cell(row=i, column=8, value=b.user_phone)
        ws.cell(row=i, column=9, value=b.status)
        ws.cell(row=i, column=10, value=b.created_at.isoformat(sep=" ", timespec="minutes") if b.created_at else "—")
    _autosize(ws)


def build_stats_workbook(
    overview: dict,
    users: list[UserStat],
    bookings: list[BookingRow],
    today: date,
    lang: str,
) -> bytes:
    wb = Workbook()
    _overview_sheet(wb.active, overview, bookings, today, lang)
    _customers_sheet(wb.create_sheet(t("xls_sheet_customers", lang)), users, lang)
    _bookings_sheet(wb.create_sheet(t("xls_sheet_bookings", lang)), bookings, lang)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
