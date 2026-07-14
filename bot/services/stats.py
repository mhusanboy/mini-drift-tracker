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
    favorite_branch: str | None


@dataclass
class BookingRow:
    date: date
    start_hour: int
    num_hours: int
    people_count: int
    status: str
    branch_name: str
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
    by_branch_rows = (
        await session.execute(
            select(Booking.branch_name, func.count(Booking.id))
            .where(confirmed)
            .group_by(Booking.branch_name)
            .order_by(Booking.branch_name)
        )
    ).all()
    return {
        "users": users,
        "bookings": bookings,
        "today": today_count,
        "by_branch": [(name, count) for name, count in by_branch_rows],
    }


async def _favorite_branch(session: AsyncSession, user_id: int) -> str | None:
    row = (
        await session.execute(
            select(Booking.branch_name, func.count(Booking.id).label("c"))
            .where(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED)
            .group_by(Booking.branch_name)
            .order_by(func.count(Booking.id).desc(), Booking.branch_name)
        )
    ).first()
    return row[0] if row else None


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
    fav = await _favorite_branch(session, user.telegram_id)
    return UserStat(
        name=user.full_name,
        phone=user.phone,
        language=user.language,
        bookings=count,
        people=people,
        first_seen=user.created_at.date() if user.created_at else None,
        last_booking=last,
        favorite_branch=fav,
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


async def all_bookings(session: AsyncSession) -> list[BookingRow]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .order_by(Booking.date, Booking.start_hour)
    )
    rows: list[BookingRow] = []
    for b in result.scalars().all():
        rows.append(
            BookingRow(
                date=b.date,
                start_hour=b.start_hour,
                num_hours=b.num_hours,
                people_count=b.people_count,
                status=b.status,
                branch_name=b.branch_name or "—",
                user_name=b.user.full_name if b.user else "—",
                user_phone=b.user.phone if b.user else "—",
                created_at=b.created_at,
            )
        )
    return rows
