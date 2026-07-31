"""Working hours, the bookable grid, and which of it is still free.

Only *accepted* bookings hold a time. Overlap is worked out on real intervals
rather than grid membership, so a booking at 18:15 still blocks 18:00 and 18:30
even though it sits off the grid.
"""
import math
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Booking, BookingStatus, Service

PEOPLE_PER_HOUR = 6
SLOT_STEP = 30          # minutes between bookable start times (:00 and :30)
MIN_BOOKING_MIN = 60    # a slot is only offered if an hour still fits
DAYS_AHEAD = 2          # today + tomorrow


def hours_needed(people: int) -> int:
    """One hour per six people, rounded up, never less than an hour."""
    return max(1, math.ceil(people / PEOPLE_PER_HOUR))


def next_days(today: date, count: int = DAYS_AHEAD) -> list[date]:
    return [today + timedelta(days=i) for i in range(count)]


# --- Working hours ----------------------------------------------------------

def has_hours(service: Service | None) -> bool:
    return service is not None and None not in (
        service.open_hour, service.open_minute, service.close_hour, service.close_minute,
    )


def opens_at(service: Service) -> int:
    return service.open_hour * 60 + service.open_minute


def closes_at(service: Service) -> int:
    return service.close_hour * 60 + service.close_minute


def grid(service: Service) -> list[int]:
    """Every start time on the 30-minute grid where an hour still fits before
    closing. The first one is rounded up to the grid from the opening time."""
    start = ((opens_at(service) + SLOT_STEP - 1) // SLOT_STEP) * SLOT_STEP
    close = closes_at(service)
    out = []
    while start + MIN_BOOKING_MIN <= close:
        out.append(start)
        start += SLOT_STEP
    return out


# --- Overlap ----------------------------------------------------------------

def span(booking: Booking) -> tuple[int, int]:
    """The [start, end) minutes a booking occupies on its day."""
    return booking.start_minute, booking.start_minute + booking.duration_hours * 60


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


async def accepted_on(session: AsyncSession, day: date) -> list[Booking]:
    """Accepted bookings that hold a time on this day."""
    result = await session.execute(
        select(Booking).where(
            Booking.date == day,
            Booking.status == BookingStatus.ACCEPTED,
            Booking.start_minute.is_not(None),
        ).order_by(Booking.start_minute)
    )
    return list(result.scalars().all())


def free_slots(
    service: Service, taken: list[Booking], day: date, now: datetime
) -> list[int]:
    """Grid starts still free, skipping anything already past today."""
    now_min = now.hour * 60 + now.minute if day == now.date() else -1
    return [
        start for start in grid(service)
        if start > now_min
        and not any(overlaps((start, start + MIN_BOOKING_MIN), span(b)) for b in taken)
    ]


def covered_by(taken: list[Booking], minute: int) -> Booking | None:
    """The accepted booking occupying this start minute, if any."""
    for b in taken:
        if b.start_minute <= minute < b.start_minute + b.duration_hours * 60:
            return b
    return None


def day_schedule(
    service: Service, taken: list[Booking], day: date, now: datetime
) -> list[tuple[int, bool]]:
    """Every grid start for the day as ``(minute, busy)`` — busy meaning an
    accepted booking sits on it. Past starts are dropped for today."""
    now_min = now.hour * 60 + now.minute if day == now.date() else -1
    return [
        (start, covered_by(taken, start) is not None)
        for start in grid(service) if start > now_min
    ]


async def conflicts_for(session: AsyncSession, booking: Booking) -> list[Booking]:
    """Accepted bookings whose time clashes with this one. Empty when the
    booking holds no time yet."""
    if booking.date is None or booking.start_minute is None:
        return []
    mine = span(booking)
    return [
        other for other in await accepted_on(session, booking.date)
        if other.id != booking.id and overlaps(mine, span(other))
    ]
