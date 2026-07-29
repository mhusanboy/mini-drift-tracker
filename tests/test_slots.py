from datetime import date, datetime, timedelta

from sqlalchemy import select

from bot.db.models import Booking, BookingStatus, Branch, User
from bot.services import slots

D = date(2026, 7, 20)  # a future booking day


def test_next_days_is_today_and_tomorrow():
    days = slots.next_days(date(2026, 7, 15))
    assert days == [date(2026, 7, 15), date(2026, 7, 16)]


def test_hours_needed():
    assert slots.hours_needed(6) == 1
    assert slots.hours_needed(7) == 2
    assert slots.hours_needed(13) == 3


async def _seed(session_factory, open_hour=10, open_minute=0, close_hour=14, close_minute=0):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=open_hour, open_minute=open_minute,
                     close_hour=close_hour, close_minute=close_minute, is_active=True))
        await s.commit()


async def test_get_service_and_upsert(session_factory):
    async with session_factory() as s:
        assert await slots.get_service(s) is None
        await slots.upsert_service(s, name="Kart", address="A", open_hour=10, open_minute=0,
                                   close_hour=22, close_minute=0, latitude=None, longitude=None,
                                   location_url=None)
    async with session_factory() as s:
        await slots.upsert_service(s, name="Kart2", address="B", open_hour=9, open_minute=30,
                                   close_hour=23, close_minute=0, latitude=41.0, longitude=69.0,
                                   location_url=None)
        svc = await slots.get_service(s)
        assert svc.name == "Kart2"
        assert len((await s.execute(select(Branch))).scalars().all()) == 1


async def test_day_off_toggle_and_bookable_days(session_factory):
    await _seed(session_factory)
    d1 = date(2026, 7, 16)
    async with session_factory() as s:
        assert await slots.toggle_day_off(s, d1) is True
        # today+tomorrow = 15,16; 16 is off -> only 15
        assert await slots.bookable_days(s, date(2026, 7, 15)) == [date(2026, 7, 15)]
        assert await slots.toggle_day_off(s, d1) is False


async def test_free_slots_half_hour_grid(session_factory):
    await _seed(session_factory)  # 10:00-14:00
    async with session_factory() as s:
        svc = await slots.get_service(s)
        avail = await slots.free_slots(s, svc, D, datetime(2026, 7, 13, 8, 0))
        # 10:00..13:00 in 30-min steps (13:00 + 1h = 14:00 close); 13:30 excluded
        assert avail == [600, 630, 660, 690, 720, 750, 780]


async def test_free_slots_half_hour_opening_offset(session_factory):
    await _seed(session_factory, open_hour=11, open_minute=30)  # opens 11:30
    async with session_factory() as s:
        svc = await slots.get_service(s)
        avail = await slots.free_slots(s, svc, D, datetime(2026, 7, 13, 8, 0))
        assert avail == [690, 720, 750, 780]  # 11:30, 12:00, 12:30, 13:00


async def test_free_slots_excludes_full_span_and_matches_example(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Book 11:30 (690) for 3 people -> 1h -> covers 11:30 and 12:00.
        b = await slots.create_booking(s, 1, 1, D, 690, 3)
        assert b is not None and b.start_minute == 690 and b.num_hours == 1
        svc = await slots.get_service(s)
        avail = await slots.free_slots(s, svc, D, datetime(2026, 7, 13, 8, 0))
        # 11:30(690) and 12:00(720) gone; 11:00(660) and 12:30(750) remain
        assert 690 not in avail and 720 not in avail
        assert 660 in avail and 750 in avail


async def test_free_slots_day_off_empty(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        svc = await slots.get_service(s)
        assert await slots.free_slots(s, svc, D, datetime(2026, 7, 13, 8, 0), day_off=True) == []


async def test_free_slots_excludes_past_today(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        svc = await slots.get_service(s)
        avail = await slots.free_slots(s, svc, date(2026, 7, 13), datetime(2026, 7, 13, 11, 15))
        assert avail == [690, 720, 750, 780]  # 11:30 onward (11:00 is past)


async def test_create_booking_rejects_overlap(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        assert await slots.create_booking(s, 1, 1, D, 600, 7) is not None  # 10:00 2h -> 10:00-12:00
        assert await slots.create_booking(s, 1, 1, D, 630, 1) is None      # 10:30 overlaps
        assert await slots.create_booking(s, 1, 1, D, 720, 1) is not None  # 12:00 free


async def test_create_booking_rejects_span_past_closing(session_factory):
    await _seed(session_factory)  # close 14:00 (840)
    async with session_factory() as s:
        assert await slots.create_booking(s, 1, 1, D, 780, 7) is None      # 13:00 2h -> 15:00
        assert await slots.create_booking(s, 1, 1, D, 780, 6) is not None  # 13:00 1h -> 14:00


async def test_upcoming_hides_finished(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Today 13:00, 1h. now=12:00 -> upcoming; now=13:30 -> finished (hidden)
        await slots.create_booking(s, 1, 1, date(2026, 7, 15), 780, 3)
        up = await slots.upcoming_bookings(s, 1, datetime(2026, 7, 15, 12, 0))
        assert len(up) == 1
        gone = await slots.upcoming_bookings(s, 1, datetime(2026, 7, 15, 14, 30))
        assert gone == []


async def test_due_for_reminder(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        # Booking at 13:00 today (within 10:00-14:00).
        await slots.create_booking(s, 1, 1, date(2026, 7, 15), 780, 3)
        # 90 min before -> not yet due
        assert await slots.due_for_reminder(s, datetime(2026, 7, 15, 11, 30)) == []
        # 45 min before -> due
        due = await slots.due_for_reminder(s, datetime(2026, 7, 15, 12, 15))
        assert len(due) == 1
        await slots.mark_reminded(s, due[0].id)
        # already reminded -> not due
        assert await slots.due_for_reminder(s, datetime(2026, 7, 15, 12, 15)) == []


async def test_due_for_rating_only_attended_and_finished(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 15), 600, 3)  # 10:00-11:00
        after = datetime(2026, 7, 15, 12, 0)
        # not attended -> no rating
        assert await slots.due_for_rating(s, after) == []
        await slots.set_attended(s, b.id, True)
        due = await slots.due_for_rating(s, after)
        assert len(due) == 1
        # before end -> not due
        assert await slots.due_for_rating(s, datetime(2026, 7, 15, 10, 30)) == []
        await slots.mark_rating_requested(s, b.id)
        assert await slots.due_for_rating(s, after) == []


async def test_set_rating_wrong_user(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, D, 600, 3)
        assert await slots.set_rating(s, b.id, 999, 5) is None
        ok = await slots.set_rating(s, b.id, 1, 4)
        assert ok.rating == 4
