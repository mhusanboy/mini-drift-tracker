from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, Branch


def next_days(today: date, count: int = 7) -> list[date]:
    return [today + timedelta(days=i) for i in range(count)]


async def list_active_branches(session: AsyncSession) -> list[Branch]:
    result = await session.execute(
        select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name)
    )
    return list(result.scalars().all())


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    return await session.get(Branch, branch_id)


async def free_hours(
    session: AsyncSession, branch: Branch, day: date, now: datetime
) -> list[int]:
    result = await session.execute(
        select(Booking.start_hour).where(
            Booking.branch_id == branch.id,
            Booking.date == day,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booked = set(result.scalars().all())
    hours = []
    for hour in range(branch.open_hour, branch.close_hour):
        if hour in booked:
            continue
        if day == now.date() and hour <= now.hour:
            continue
        hours.append(hour)
    return hours


async def create_booking(
    session: AsyncSession,
    user_id: int,
    branch_id: int,
    day: date,
    hour: int,
    people: int,
) -> Booking | None:
    booking = Booking(
        user_id=user_id,
        branch_id=branch_id,
        date=day,
        start_hour=hour,
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
