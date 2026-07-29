import math
from datetime import date, datetime, time as dt_time, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, Branch, DayOff

PEOPLE_PER_HOUR = 6
SLOT_STEP = 30           # minutes between bookable start times (:00 and :30)
DAYS_AHEAD = 2           # today + tomorrow
REMINDER_LEAD_MIN = 60   # send the "are you coming?" reminder ~1h before


def next_days(today: date, count: int = DAYS_AHEAD) -> list[date]:
    return [today + timedelta(days=i) for i in range(count)]


def hours_needed(people: int) -> int:
    """Hours to book for a group: 1h per 6 people, rounded up (min 1)."""
    return max(1, math.ceil(people / PEOPLE_PER_HOUR))


def _start_dt(b: Booking) -> datetime:
    return datetime.combine(b.date, dt_time()) + timedelta(minutes=b.start_minute)


def _end_dt(b: Booking) -> datetime:
    return datetime.combine(b.date, dt_time()) + timedelta(minutes=b.start_minute + b.num_hours * 60)


# --- Single service (stored as the sole row of the branches table) ----------

async def get_service(session: AsyncSession) -> Branch | None:
    return (
        await session.execute(select(Branch).order_by(Branch.id).limit(1))
    ).scalar_one_or_none()


async def upsert_service(
    session: AsyncSession, *, name, address, open_hour, open_minute,
    close_hour, close_minute, latitude, longitude, location_url,
) -> Branch:
    service = await get_service(session)
    if service is None:
        service = Branch(is_active=True)
        session.add(service)
    service.name = name
    service.address = address
    service.open_hour = open_hour
    service.open_minute = open_minute
    service.close_hour = close_hour
    service.close_minute = close_minute
    service.latitude = latitude
    service.longitude = longitude
    service.location_url = location_url
    await session.commit()
    await session.refresh(service)
    return service


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    return await session.get(Branch, branch_id)


# --- Day-offs ---------------------------------------------------------------

async def day_offs_in(session: AsyncSession, days: list[date]) -> set[date]:
    if not days:
        return set()
    result = await session.execute(select(DayOff.date).where(DayOff.date.in_(days)))
    return set(result.scalars().all())


async def toggle_day_off(session: AsyncSession, day: date) -> bool:
    existing = await session.get(DayOff, day)
    if existing is None:
        session.add(DayOff(date=day))
        await session.commit()
        return True
    await session.delete(existing)
    await session.commit()
    return False


async def bookable_days(session: AsyncSession, today: date, count: int = DAYS_AHEAD) -> list[date]:
    days = next_days(today, count)
    offs = await day_offs_in(session, days)
    return [d for d in days if d not in offs]


# --- Availability (30-minute slots) -----------------------------------------

def _open_minute(service: Branch) -> int:
    return service.open_hour * 60 + service.open_minute


def _close_minute(service: Branch) -> int:
    return service.close_hour * 60 + service.close_minute


def first_slot_minute(service: Branch) -> int:
    """First bookable start, rounded up to the next 30-min boundary at/after open."""
    om = _open_minute(service)
    return ((om + SLOT_STEP - 1) // SLOT_STEP) * SLOT_STEP


async def _booked_minutes(session: AsyncSession, branch_id: int, day: date) -> set[int]:
    """Every 30-min mark occupied by a confirmed booking, expanding each across
    its full [start, start + num_hours*60) span."""
    result = await session.execute(
        select(Booking.start_minute, Booking.num_hours).where(
            Booking.branch_id == branch_id,
            Booking.date == day,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booked: set[int] = set()
    for start_minute, num_hours in result.all():
        booked.update(range(start_minute, start_minute + num_hours * 60, SLOT_STEP))
    return booked


async def free_slots(
    session: AsyncSession, service: Branch, day: date, now: datetime,
    day_off: bool = False,
) -> list[int]:
    """Start minutes (30-min grid) that are individually free. Empty on a
    day-off. The group's full span is validated in create_booking."""
    if day_off:
        return []
    booked = await _booked_minutes(session, service.id, day)
    close = _close_minute(service)
    now_min = now.hour * 60 + now.minute
    out = []
    start = first_slot_minute(service)
    while start + 60 <= close:  # a minimum 1-hour booking must still fit
        if start not in booked and not (day == now.date() and start <= now_min):
            out.append(start)
        start += SLOT_STEP
    return out


def span_fits(service: Branch, start_minute: int, num_hours: int) -> bool:
    return start_minute + num_hours * 60 <= _close_minute(service)


async def create_booking(
    session: AsyncSession,
    user_id: int,
    branch_id: int,
    day: date,
    start_minute: int,
    people: int,
) -> Booking | None:
    """Create a confirmed booking spanning ``hours_needed(people)`` hours from
    ``start_minute``. Returns ``None`` if it runs past closing or overlaps an
    already-booked slot."""
    num_hours = hours_needed(people)
    branch = await session.get(Branch, branch_id)
    if branch is None or not span_fits(branch, start_minute, num_hours):
        return None

    booked = await _booked_minutes(session, branch_id, day)
    if any(m in booked for m in range(start_minute, start_minute + num_hours * 60, SLOT_STEP)):
        return None

    booking = Booking(
        user_id=user_id,
        branch_id=branch_id,
        branch_name=branch.name,
        date=day,
        start_minute=start_minute,
        num_hours=num_hours,
        people_count=people,
        status=BookingStatus.CONFIRMED,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return None
    await session.refresh(booking)
    return booking


async def cancel_booking(
    session: AsyncSession, booking_id: int, user_id: int
) -> Booking | None:
    result = await session.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        return None
    booking.status = BookingStatus.CANCELLED
    await session.commit()
    return booking


async def upcoming_bookings(
    session: AsyncSession, user_id: int, now: datetime
) -> list[Booking]:
    """Confirmed bookings not yet finished (end time still in the future)."""
    result = await session.execute(
        select(Booking).where(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        ).order_by(Booking.date, Booking.start_minute)
    )
    return [b for b in result.scalars().all() if _end_dt(b) > now]


# --- Scheduler support ------------------------------------------------------

async def due_for_reminder(session: AsyncSession, now: datetime) -> list[Booking]:
    """Confirmed, not-yet-reminded bookings starting within the next hour."""
    horizon = now + timedelta(minutes=REMINDER_LEAD_MIN)
    result = await session.execute(
        select(Booking).options(selectinload(Booking.user)).where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.reminded.is_(False),
        )
    )
    return [b for b in result.scalars().all() if now < _start_dt(b) <= horizon]


async def due_for_rating(session: AsyncSession, now: datetime) -> list[Booking]:
    """Attended bookings that have finished and not yet been asked to rate."""
    result = await session.execute(
        select(Booking).options(selectinload(Booking.user)).where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.attended.is_(True),
            Booking.rating_requested.is_(False),
        )
    )
    return [b for b in result.scalars().all() if _end_dt(b) <= now]


async def mark_reminded(session: AsyncSession, booking_id: int) -> None:
    b = await session.get(Booking, booking_id)
    if b is not None:
        b.reminded = True
        await session.commit()


async def mark_rating_requested(session: AsyncSession, booking_id: int) -> None:
    b = await session.get(Booking, booking_id)
    if b is not None:
        b.rating_requested = True
        await session.commit()


async def set_attended(session: AsyncSession, booking_id: int, value: bool) -> Booking | None:
    b = await session.get(Booking, booking_id)
    if b is None:
        return None
    b.attended = value
    await session.commit()
    return b


async def set_rating(
    session: AsyncSession, booking_id: int, user_id: int, value: int
) -> Booking | None:
    b = await session.get(Booking, booking_id)
    if b is None or b.user_id != user_id:
        return None
    b.rating = value
    await session.commit()
    return b
