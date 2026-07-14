import math
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, Branch

PEOPLE_PER_HOUR = 6


def next_days(today: date, count: int = 7) -> list[date]:
    return [today + timedelta(days=i) for i in range(count)]


def hours_needed(people: int) -> int:
    """Hours to book for a group: 1h per 6 people, rounded up (min 1)."""
    return max(1, math.ceil(people / PEOPLE_PER_HOUR))


async def list_active_branches(session: AsyncSession) -> list[Branch]:
    result = await session.execute(
        select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name)
    )
    return list(result.scalars().all())


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    return await session.get(Branch, branch_id)


async def _booked_hours(session: AsyncSession, branch_id: int, day: date) -> set[int]:
    """Every clock hour occupied by a confirmed booking on that branch/day,
    expanding each booking across its full [start, start + num_hours) span."""
    result = await session.execute(
        select(Booking.start_hour, Booking.num_hours).where(
            Booking.branch_id == branch_id,
            Booking.date == day,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booked: set[int] = set()
    for start_hour, num_hours in result.all():
        booked.update(range(start_hour, start_hour + num_hours))
    return booked


async def free_hours(
    session: AsyncSession, branch: Branch, day: date, now: datetime
) -> list[int]:
    """Start hours that are individually free. The group's full span is
    validated later (once the people count is known) via ``create_booking``."""
    booked = await _booked_hours(session, branch.id, day)
    hours = []
    for hour in range(branch.open_hour, branch.close_hour):
        if hour in booked:
            continue
        if day == now.date() and hour <= now.hour:
            continue
        hours.append(hour)
    return hours


def span_fits(branch: Branch, start_hour: int, num_hours: int) -> bool:
    """True if a booking of ``num_hours`` starting at ``start_hour`` ends by
    the branch's closing hour."""
    return start_hour + num_hours <= branch.close_hour


async def create_booking(
    session: AsyncSession,
    user_id: int,
    branch_id: int,
    day: date,
    hour: int,
    people: int,
) -> Booking | None:
    """Create a confirmed booking spanning ``hours_needed(people)`` consecutive
    hours. Returns ``None`` if the span would run past closing time or overlaps
    any already-booked hour (SQLite serializes writes, so the read-then-insert
    is effectively atomic for this single-process bot)."""
    num_hours = hours_needed(people)
    branch = await session.get(Branch, branch_id)
    if branch is None or not span_fits(branch, hour, num_hours):
        return None

    booked = await _booked_hours(session, branch_id, day)
    if any(h in booked for h in range(hour, hour + num_hours)):
        return None

    booking = Booking(
        user_id=user_id,
        branch_id=branch_id,
        date=day,
        start_hour=hour,
        num_hours=num_hours,
        people_count=people,
        status=BookingStatus.CONFIRMED,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError:
        # Backstop for the exact-start-hour partial unique index under a race.
        await session.rollback()
        return None
    await session.refresh(booking)
    return booking


async def cancel_booking(
    session: AsyncSession, booking_id: int, user_id: int
) -> Booking | None:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.branch))
        .where(
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
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.branch))
        .where(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
        .order_by(Booking.date, Booking.start_hour)
    )
    out = []
    for b in result.scalars().all():
        if b.date > now.date() or (b.date == now.date() and b.start_hour >= now.hour):
            out.append(b)
    return out
