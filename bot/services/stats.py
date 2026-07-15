import math
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, User


@dataclass
class UserStat:
    name: str
    phone: str
    language: str
    bookings: int
    people: int
    first_seen: date | None
    last_booking: date | None


@dataclass
class BookingRow:
    id: int
    date: date
    start_minute: int
    num_hours: int
    people_count: int
    status: str
    attended: bool | None
    user_name: str
    user_phone: str
    created_at: datetime | None


def _end_dt(day: date, start_minute: int, num_hours: int) -> datetime:
    return datetime.combine(day, dt_time()) + timedelta(minutes=start_minute + num_hours * 60)


async def overview(session: AsyncSession, today: date) -> dict:
    users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    confirmed = Booking.status == BookingStatus.CONFIRMED
    bookings = (
        await session.execute(select(func.count()).select_from(Booking).where(confirmed))
    ).scalar_one()
    today_count = (
        await session.execute(
            select(func.count()).select_from(Booking).where(confirmed, Booking.date == today)
        )
    ).scalar_one()
    people = (
        await session.execute(
            select(func.coalesce(func.sum(Booking.people_count), 0)).where(confirmed)
        )
    ).scalar_one()
    hours = (
        await session.execute(
            select(func.coalesce(func.sum(Booking.num_hours), 0)).where(confirmed)
        )
    ).scalar_one()
    return {
        "users": users,
        "bookings": bookings,
        "today": today_count,
        "people": int(people),
        "hours": int(hours),
    }


async def _user_stat(session: AsyncSession, user: User) -> UserStat:
    confirmed = Booking.status == BookingStatus.CONFIRMED
    agg = (
        await session.execute(
            select(
                func.count(Booking.id),
                func.coalesce(func.sum(Booking.people_count), 0),
                func.max(Booking.date),
            ).where(Booking.user_id == user.telegram_id, confirmed)
        )
    ).first()
    count, people, last = agg[0], int(agg[1]), agg[2]
    return UserStat(
        name=user.full_name,
        phone=user.phone,
        language=user.language,
        bookings=count,
        people=people,
        first_seen=user.created_at.date() if user.created_at else None,
        last_booking=last,
    )


async def user_stats_page(
    session: AsyncSession, page: int, per_page: int = 5
) -> tuple[list[UserStat], int]:
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    total_pages = max(1, math.ceil(total_users / per_page))
    page = max(1, min(page, total_pages))
    users = (
        await session.execute(
            select(User).order_by(User.created_at, User.telegram_id)
            .limit(per_page).offset((page - 1) * per_page)
        )
    ).scalars().all()
    return [await _user_stat(session, u) for u in users], total_pages


async def all_user_stats(session: AsyncSession) -> list[UserStat]:
    users = (
        await session.execute(
            select(User).order_by(User.created_at, User.telegram_id)
        )
    ).scalars().all()
    return [await _user_stat(session, u) for u in users]


def _to_row(b: Booking) -> BookingRow:
    return BookingRow(
        id=b.id,
        date=b.date,
        start_minute=b.start_minute,
        num_hours=b.num_hours,
        people_count=b.people_count,
        status=b.status,
        attended=b.attended,
        user_name=b.user.full_name if b.user else "—",
        user_phone=b.user.phone if b.user else "—",
        created_at=b.created_at,
    )


async def all_bookings(session: AsyncSession) -> list[BookingRow]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .order_by(Booking.date, Booking.start_minute)
    )
    return [_to_row(b) for b in result.scalars().all()]


async def bookings_on_day(session: AsyncSession, day: date, now: datetime) -> list[BookingRow]:
    """Confirmed, not-yet-finished bookings for a day (finished ones disappear)."""
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .where(Booking.date == day, Booking.status == BookingStatus.CONFIRMED)
        .order_by(Booking.start_minute)
    )
    return [
        _to_row(b) for b in result.scalars().all()
        if _end_dt(b.date, b.start_minute, b.num_hours) > now
    ]


async def booking_counts(session: AsyncSession, days: list[date], now: datetime) -> dict[date, int]:
    """Count of not-yet-finished confirmed bookings per day (for the day picker)."""
    return {d: len(await bookings_on_day(session, d, now)) for d in days}
