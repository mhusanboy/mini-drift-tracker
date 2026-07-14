from datetime import date, datetime

from bot.db.models import Branch, BookingStatus, User
from bot.services import slots


def test_next_days_count_and_start():
    days = slots.next_days(date(2026, 7, 13), 7)
    assert len(days) == 7
    assert days[0] == date(2026, 7, 13)
    assert days[-1] == date(2026, 7, 19)


async def _seed(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=10, close_hour=14, is_active=True))
        s.add(Branch(id=2, name="Old", address="Y", open_hour=9, close_hour=12, is_active=False))
        await s.commit()


async def test_list_active_branches(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        branches = await slots.list_active_branches(s)
        assert [b.id for b in branches] == [1]


async def test_free_hours_full_range_future_day(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [10, 11, 12, 13]


async def test_free_hours_excludes_booked(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 11, 2)
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [10, 12, 13]


async def test_free_hours_excludes_past_hours_today(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 13), datetime(2026, 7, 13, 11, 30))
        assert hours == [12, 13]


async def test_create_booking_double_returns_none(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        first = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        assert first is not None
        second = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 4)
        assert second is None


async def test_cancel_frees_slot_and_allows_rebook(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        cancelled = await slots.cancel_booking(s, b.id, user_id=1)
        assert cancelled.status == BookingStatus.CANCELLED
        again = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 3)
        assert again is not None


async def test_cancel_wrong_user_returns_none(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        assert await slots.cancel_booking(s, b.id, user_id=999) is None


async def test_upcoming_bookings_sorted_and_confirmed_only(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 13, 2)
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        await slots.create_booking(s, 1, 1, date(2026, 7, 12), 10, 2)
        up = await slots.upcoming_bookings(s, 1, datetime(2026, 7, 13, 9, 0))
        assert [(x.date, x.start_hour) for x in up] == [(date(2026, 7, 20), 10), (date(2026, 7, 20), 13)]
