from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook

from bot.db.models import BookingStatus
from bot.services.export import build_stats_workbook
from bot.services.stats import BookingRow, UserStat


def _sample():
    overview = {"users": 2, "bookings": 3, "today": 1, "by_branch": [("Main", 2), ("North", 1)]}
    users = [
        UserStat(name="Anvar", phone="+1", language="uz", bookings=2, people=9,
                 first_seen=date(2026, 7, 1), last_booking=date(2026, 7, 20),
                 favorite_branch="Main"),
        UserStat(name="Bek", phone="+2", language="ru", bookings=1, people=4,
                 first_seen=date(2026, 7, 2), last_booking=date(2026, 7, 13),
                 favorite_branch="North"),
    ]
    bookings = [
        BookingRow(date=date(2026, 7, 20), start_hour=10, num_hours=2, people_count=9,
                   status=BookingStatus.CONFIRMED, branch_name="Main", user_name="Anvar",
                   user_phone="+1", created_at=datetime(2026, 7, 13, 9, 0)),
        BookingRow(date=date(2026, 7, 13), start_hour=15, num_hours=1, people_count=4,
                   status=BookingStatus.CONFIRMED, branch_name="North", user_name="Bek",
                   user_phone="+2", created_at=datetime(2026, 7, 12, 8, 0)),
        BookingRow(date=date(2026, 7, 21), start_hour=12, num_hours=1, people_count=2,
                   status=BookingStatus.CANCELLED, branch_name="Main", user_name="Anvar",
                   user_phone="+1", created_at=datetime(2026, 7, 13, 10, 0)),
    ]
    return overview, users, bookings


def test_workbook_has_three_localized_sheets_ru():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    assert wb.sheetnames == ["Обзор", "Клиенты", "Брони"]


def test_workbook_sheets_localized_uz():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "uz")
    wb = load_workbook(BytesIO(data))
    assert wb.sheetnames == ["Umumiy", "Mijozlar", "Bronlar"]


def test_customers_sheet_content():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    ws = wb["Клиенты"]
    # Header row + two customer rows.
    assert ws.cell(row=1, column=1).value == "Имя"
    names = {ws.cell(row=r, column=1).value for r in (2, 3)}
    assert names == {"Anvar", "Bek"}


def test_bookings_sheet_lists_all_statuses():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    ws = wb["Брони"]
    statuses = {ws.cell(row=r, column=9).value for r in (2, 3, 4)}
    assert statuses == {"confirmed", "cancelled"}
    # 10:00 + 2h -> end 12:00 on the first (sorted) booking.
    assert ws.cell(row=2, column=3).value == "12:00"


def test_overview_branch_breakdown_uses_confirmed_only():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    ws = wb["Обзор"]
    # Find the "Main" branch row in the breakdown and check its confirmed count (1, not 2
    # — the cancelled Main booking is excluded from the per-branch totals).
    main_hours = None
    for row in ws.iter_rows(values_only=True):
        if row and row[0] == "Main":
            main_hours = row[3]
    assert main_hours == 2  # single confirmed Main booking spanning 2 hours
