from datetime import date, datetime

from sqlalchemy import select

from bot.db.models import Booking, Branch, BookingStatus, User
from bot.services import slots


def test_next_days_count_and_start():
    days = slots.next_days(date(2026, 7, 13), 7)
    assert len(days) == 7
    assert days[0] == date(2026, 7, 13)
    assert days[-1] == date(2026, 7, 19)


def test_hours_needed():
    assert slots.hours_needed(1) == 1
    assert slots.hours_needed(6) == 1
    assert slots.hours_needed(7) == 2
    assert slots.hours_needed(12) == 2
    assert slots.hours_needed(13) == 3


async def _seed(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=10, close_hour=14, is_active=True))
        await s.commit()


async def test_get_service_returns_the_single_row(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        service = await slots.get_service(s)
        assert service is not None and service.name == "Main"


async def test_get_service_none_when_empty(session_factory):
    async with session_factory() as s:
        assert await slots.get_service(s) is None


async def test_upsert_service_creates_then_updates(session_factory):
    async with session_factory() as s:
        created = await slots.upsert_service(
            s, name="Kart", address="A", open_hour=10, open_minute=0,
            close_hour=22, close_minute=0, latitude=None, longitude=None, location_url=None)
        assert created.name == "Kart"
    async with session_factory() as s:
        updated = await slots.upsert_service(
            s, name="Kart2", address="B", open_hour=9, open_minute=30,
            close_hour=23, close_minute=0, latitude=41.0, longitude=69.0, location_url=None)
        # Still a single service row, now updated.
        assert updated.name == "Kart2"
        all_rows = (await s.execute(select(Branch))).scalars().all()
        assert len(all_rows) == 1


async def test_day_off_toggle_and_bookable_days(session_factory):
    await _seed(session_factory)
    d1 = date(2026, 7, 20)
    async with session_factory() as s:
        assert await slots.toggle_day_off(s, d1) is True   # now off
        assert await slots.day_offs_in(s, [d1]) == {d1}
        days = await slots.bookable_days(s, date(2026, 7, 20), count=3)  # 20,21,22 minus 20
        assert days == [date(2026, 7, 21), date(2026, 7, 22)]
        assert await slots.toggle_day_off(s, d1) is False  # back to working
        assert await slots.day_offs_in(s, [d1]) == set()


async def test_free_hours_empty_on_day_off(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.get_branch(s, 1)
        assert await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0), day_off=True) == []


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


async def test_free_hours_offset_by_half_hour_opening(session_factory):
    async with session_factory() as s:
        # Opens 11:30, closes 14:00 -> first slot is the next full hour (12:00).
        s.add(Branch(id=5, name="Half", address="Z", open_hour=11, open_minute=30,
                     close_hour=14, close_minute=0, is_active=True))
        await s.commit()
        b = await slots.get_branch(s, 5)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [12, 13]
        assert slots.first_slot_hour(b) == 12


async def test_free_hours_on_the_hour_opening_unchanged(session_factory):
    async with session_factory() as s:
        s.add(Branch(id=6, name="Whole", address="Z", open_hour=11, open_minute=0,
                     close_hour=14, is_active=True))
        await s.commit()
        b = await slots.get_branch(s, 6)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [11, 12, 13]


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


async def test_create_booking_stores_num_hours(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # 7 people -> 2 hours
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 7)
        assert b.num_hours == 2


async def test_free_hours_excludes_full_multi_hour_span(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Branch 1: open 10, close 14. Book 10:00 for 7 people -> covers 10, 11.
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 7)
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [12, 13]


async def test_create_booking_rejects_span_past_closing(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Branch 1 closes at 14. Start 13 with 7 people needs 2h (13,14) -> past close.
        assert await slots.create_booking(s, 1, 1, date(2026, 7, 20), 13, 7) is None
        # A 1-hour booking at 13 fits (ends at 14).
        assert await slots.create_booking(s, 1, 1, date(2026, 7, 20), 13, 6) is not None


async def test_create_booking_rejects_overlap_with_different_start(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Book 10:00 for 2h (covers 10, 11).
        assert await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 7) is not None
        # Booking starting at 11 overlaps the second hour of the first booking.
        assert await slots.create_booking(s, 1, 1, date(2026, 7, 20), 11, 1) is None
        # 12:00 is free.
        assert await slots.create_booking(s, 1, 1, date(2026, 7, 20), 12, 1) is not None


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
