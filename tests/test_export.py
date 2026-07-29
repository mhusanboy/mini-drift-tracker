from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook

from bot.db.models import BookingStatus
from bot.services.export import build_stats_workbook
from bot.services.stats import BookingRow, UserStat


def _sample():
    overview = {"users": 2, "bookings": 3, "today": 1, "people": 15, "hours": 4}
    users = [
        UserStat(name="Anvar", phone="+1", language="uz", bookings=2, people=9,
                 first_seen=date(2026, 7, 1), last_booking=date(2026, 7, 20)),
        UserStat(name="Bek", phone="+2", language="ru", bookings=1, people=4,
                 first_seen=date(2026, 7, 2), last_booking=date(2026, 7, 13)),
    ]
    bookings = [
        BookingRow(id=1, date=date(2026, 7, 20), start_minute=600, num_hours=2, people_count=9,
                   status=BookingStatus.CONFIRMED, attended=True, user_name="Anvar",
                   user_phone="+1", created_at=datetime(2026, 7, 13, 9, 0)),
        BookingRow(id=2, date=date(2026, 7, 13), start_minute=900, num_hours=1, people_count=4,
                   status=BookingStatus.CONFIRMED, attended=None, user_name="Bek",
                   user_phone="+2", created_at=datetime(2026, 7, 12, 8, 0)),
        BookingRow(id=3, date=date(2026, 7, 21), start_minute=720, num_hours=1, people_count=2,
                   status=BookingStatus.CANCELLED, attended=False, user_name="Anvar",
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
    assert ws.cell(row=1, column=1).value == "Имя"
    names = {ws.cell(row=r, column=1).value for r in (2, 3)}
    assert names == {"Anvar", "Bek"}


def test_bookings_sheet_lists_all_statuses():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    ws = wb["Брони"]
    # Columns: date, start, end, hours, people, customer, phone, status(8), created(9).
    statuses = {ws.cell(row=r, column=8).value for r in (2, 3, 4)}
    assert statuses == {"confirmed", "cancelled"}
    # 10:00 (600 min) + 2h -> end 12:00 on the first (sorted) booking.
    assert ws.cell(row=2, column=2).value == "10:00"
    assert ws.cell(row=2, column=3).value == "12:00"


def test_overview_sheet_has_metrics():
    overview, users, bookings = _sample()
    data = build_stats_workbook(overview, users, bookings, date(2026, 7, 14), "ru")
    wb = load_workbook(BytesIO(data))
    flat = [c for row in wb["Обзор"].iter_rows(values_only=True) for c in row]
    assert 15 in flat  # total people metric
    assert 4 in flat   # total hours metric
