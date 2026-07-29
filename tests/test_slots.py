from datetime import date, datetime

import pytest

from bot.db.models import Booking, BookingStatus, Service, User
from bot.services import slots

DAY = date(2026, 7, 20)
BEFORE_OPEN = datetime(2026, 7, 19, 9, 0)   # a different day: nothing is "past"


def _service(open_h=11, close_h=22, open_m=0, close_m=0):
    return Service(id=1, open_hour=open_h, open_minute=open_m,
                   close_hour=close_h, close_minute=close_m)


def _booking(start_minute, hours=1, people=2, status=BookingStatus.ACCEPTED):
    return Booking(user_id=1, full_name="A", phone="+1", date=DAY,
                   start_minute=start_minute, duration_hours=hours,
                   people_count=people, status=status)


@pytest.mark.parametrize("people,hours", [
    (1, 1), (5, 1), (6, 1),      # up to six fit in an hour
    (7, 2), (12, 2),             # a seventh person needs a second hour
    (13, 3), (18, 3),
])
def test_hours_needed(people, hours):
    assert slots.hours_needed(people) == hours


def test_hours_needed_never_returns_zero():
    assert slots.hours_needed(0) == 1


def test_grid_stops_when_an_hour_no_longer_fits():
    # 11:00-14:00 -> the last start is 13:00, because 13:30 would run over.
    assert slots.grid(_service(11, 14)) == [660, 690, 720, 750, 780]


def test_grid_rounds_the_first_slot_up_to_the_half_hour():
    assert slots.grid(_service(11, 14, open_m=10))[0] == 690  # 11:10 -> 11:30


def test_has_hours():
    assert slots.has_hours(None) is False
    assert slots.has_hours(Service(id=1)) is False
    assert slots.has_hours(_service()) is True


def test_free_slots_drop_the_whole_span_of_a_booking():
    taken = [_booking(11 * 60, hours=2)]   # 11:00-13:00
    free = slots.free_slots(_service(11, 14), taken, DAY, BEFORE_OPEN)
    assert free == [780]                   # only 13:00 survives


def test_an_off_grid_booking_still_blocks_the_slots_it_overlaps():
    # 18:15-19:15 isn't on the grid, but it must still take out 18:00 and 19:00.
    taken = [_booking(18 * 60 + 15, hours=1)]
    free = slots.free_slots(_service(17, 21), taken, DAY, BEFORE_OPEN)
    assert 17 * 60 in free and 17 * 60 + 30 not in free  # 17:30-18:30 overlaps
    assert 18 * 60 not in free and 18 * 60 + 30 not in free
    assert 19 * 60 + 30 in free


def test_only_accepted_bookings_hold_a_time():
    for status in (BookingStatus.PENDING, BookingStatus.REJECTED):
        free = slots.free_slots(_service(11, 14), [], DAY, BEFORE_OPEN)
        assert 660 in free, status


def test_slots_already_past_today_are_not_offered():
    now = datetime(2026, 7, 20, 12, 15)
    free = slots.free_slots(_service(11, 14), [], DAY, now)
    assert free == [750, 780]   # 12:30 and 13:00


def test_overlaps_is_half_open():
    # A booking ending at 12:00 does not clash with one starting at 12:00.
    assert slots.overlaps((660, 720), (720, 780)) is False
    assert slots.overlaps((660, 721), (720, 780)) is True


async def test_accepted_on_ignores_pending_and_rejected(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(_booking(11 * 60, status=BookingStatus.ACCEPTED))
        s.add(_booking(12 * 60, status=BookingStatus.PENDING))
        s.add(_booking(13 * 60, status=BookingStatus.REJECTED))
        await s.commit()
    async with session_factory() as s:
        found = await slots.accepted_on(s, DAY)
    assert [b.start_minute for b in found] == [660]


async def test_accepted_without_a_time_is_skipped(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Booking(user_id=1, date=DAY, start_minute=None,
                      status=BookingStatus.ACCEPTED))
        await s.commit()
    async with session_factory() as s:
        assert await slots.accepted_on(s, DAY) == []


async def test_conflicts_for_finds_the_overlap(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(_booking(18 * 60, hours=2))       # 18:00-20:00, accepted
        await s.commit()
    candidate = _booking(19 * 60, status=BookingStatus.PENDING)
    async with session_factory() as s:
        clashes = await slots.conflicts_for(s, candidate)
    assert len(clashes) == 1


async def test_conflicts_for_ignores_a_booking_against_itself(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        booking = _booking(18 * 60)
        s.add(booking)
        await s.commit()
        await s.refresh(booking)
    async with session_factory() as s:
        assert await slots.conflicts_for(s, booking) == []


async def test_a_request_with_no_time_conflicts_with_nothing(session_factory):
    async with session_factory() as s:
        assert await slots.conflicts_for(s, _booking(None)) == []
