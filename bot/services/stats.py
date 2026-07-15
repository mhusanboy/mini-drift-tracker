import math
from dataclasses import dataclass
from datetime import date, datetime

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
    date: date
    start_hour: int
    num_hours: int
    people_count: int
    status: str
    user_name: str
    user_phone: str
    created_at: datetime | None


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
        date=b.date,
        start_hour=b.start_hour,
        num_hours=b.num_hours,
        people_count=b.people_count,
        status=b.status,
        user_name=b.user.full_name if b.user else "—",
        user_phone=b.user.phone if b.user else "—",
        created_at=b.created_at,
    )


async def all_bookings(session: AsyncSession) -> list[BookingRow]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .order_by(Booking.date, Booking.start_hour)
    )
    return [_to_row(b) for b in result.scalars().all()]


async def bookings_on_day(session: AsyncSession, day: date) -> list[BookingRow]:
    """Confirmed bookings for a given day, with customer info, for the admin view."""
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .where(Booking.date == day, Booking.status == BookingStatus.CONFIRMED)
        .order_by(Booking.start_hour)
    )
    return [_to_row(b) for b in result.scalars().all()]


async def booking_counts(session: AsyncSession, days: list[date]) -> dict[date, int]:
    """Confirmed booking count per day, for labelling the admin day picker."""
    if not days:
        return {}
    rows = (
        await session.execute(
            select(Booking.date, func.count(Booking.id))
            .where(Booking.date.in_(days), Booking.status == BookingStatus.CONFIRMED)
            .group_by(Booking.date)
        )
    ).all()
    return {d: c for d, c in rows}
