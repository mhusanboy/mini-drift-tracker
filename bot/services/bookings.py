"""Booking requests: raised by a customer, decided by an admin."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, User
from bot.services.slots import hours_needed
from bot.timeutil import now_local


async def create(
    session: AsyncSession, user: User, when_text: str, people: int,
    day: date | None, start_minute: int | None,
) -> Booking:
    booking = Booking(
        user_id=user.telegram_id,
        full_name=user.full_name,
        phone=user.phone,
        when_text=when_text,
        date=day,
        start_minute=start_minute,
        people_count=people,
        duration_hours=hours_needed(people),
        status=BookingStatus.PENDING,
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get(session: AsyncSession, booking_id: int) -> Booking | None:
    return await session.get(Booking, booking_id)


async def set_status(session: AsyncSession, booking_id: int, status: str) -> Booking | None:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        return None
    booking.status = status
    booking.decided_at = now_local()
    await session.commit()
    await session.refresh(booking)
    return booking


async def set_time(
    session: AsyncSession, booking_id: int, day: date, start_minute: int
) -> Booking | None:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        return None
    booking.date = day
    booking.start_minute = start_minute
    await session.commit()
    await session.refresh(booking)
    return booking


async def set_people(session: AsyncSession, booking_id: int, people: int) -> Booking | None:
    """Duration follows the people count, unless an admin has pinned it."""
    booking = await session.get(Booking, booking_id)
    if booking is None:
        return None
    booking.people_count = people
    if not booking.duration_overridden:
        booking.duration_hours = hours_needed(people)
    await session.commit()
    await session.refresh(booking)
    return booking


async def set_duration(session: AsyncSession, booking_id: int, hours: int) -> Booking | None:
    """Pins the duration: a later people edit will leave it alone."""
    booking = await session.get(Booking, booking_id)
    if booking is None:
        return None
    booking.duration_hours = hours
    booking.duration_overridden = True
    await session.commit()
    await session.refresh(booking)
    return booking


async def history(session: AsyncSession) -> list[Booking]:
    """Every request, newest first, with its customer loaded."""
    result = await session.execute(
        select(Booking).options(selectinload(Booking.user)).order_by(Booking.id.desc())
    )
    return list(result.scalars().all())
