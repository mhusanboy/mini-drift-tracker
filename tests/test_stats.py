from datetime import date, datetime

from bot.db.models import Branch, User
from bot.services import slots, stats


async def _seed(session_factory):
    async with session_factory() as s:
        s.add_all([
            User(telegram_id=1, full_name="Anvar", phone="+1"),
            User(telegram_id=2, full_name="Bek", phone="+2"),
            Branch(id=1, name="Main", address="X", open_hour=10, close_hour=22),
        ])
        await s.commit()
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 13), 600, 3)   # 10:00
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 660, 2)   # 11:00
        await slots.create_booking(s, 1, 1, date(2026, 7, 21), 720, 1)   # 12:00
        await slots.create_booking(s, 2, 1, date(2026, 7, 13), 900, 4)   # 15:00


async def test_overview(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        ov = await stats.overview(s, date(2026, 7, 13))
        assert ov["users"] == 2
        assert ov["bookings"] == 4
        assert ov["today"] == 2
        assert ov["people"] == 10  # 3 + 2 + 1 + 4
        assert ov["hours"] == 4     # each spans 1 hour


async def test_user_stats(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        rows, pages = await stats.user_stats_page(s, page=1, per_page=5)
        assert pages == 1
        anvar = next(r for r in rows if r.name == "Anvar")
        assert anvar.bookings == 3
        assert anvar.people == 6
        assert anvar.last_booking == date(2026, 7, 21)
        assert anvar.language == "ru"


async def test_bookings_on_day_ordered_and_future(session_factory):
    await _seed(session_factory)
    now = datetime(2026, 7, 13, 8, 0)
    async with session_factory() as s:
        rows = await stats.bookings_on_day(s, date(2026, 7, 13), now)
        assert [(r.start_minute, r.user_name) for r in rows] == [(600, "Anvar"), (900, "Bek")]


async def test_bookings_on_day_hides_finished(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # After 16:00 on 7/13 both that day's bookings (10:00, 15:00) are finished.
        rows = await stats.bookings_on_day(s, date(2026, 7, 13), datetime(2026, 7, 13, 16, 30))
        assert rows == []


async def test_booking_counts(session_factory):
    await _seed(session_factory)
    now = datetime(2026, 7, 13, 8, 0)
    async with session_factory() as s:
        counts = await stats.booking_counts(s, [date(2026, 7, 13), date(2026, 7, 20)], now)
        assert counts == {date(2026, 7, 13): 2, date(2026, 7, 20): 1}
