import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Booking, BookingStatus, Branch, User


@dataclass
class UserStat:
    name: str
    phone: str
    bookings: int
    people: int
    first_seen: date | None
    last_booking: date | None
    favorite_branch: str | None


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
            select(Branch.name, func.count(Booking.id))
            .join(Booking, Booking.branch_id == Branch.id)
            .where(confirmed)
            .group_by(Branch.id)
            .order_by(Branch.name)
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
            select(Branch.name, func.count(Booking.id).label("c"))
            .join(Booking, Booking.branch_id == Branch.id)
            .where(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED)
            .group_by(Branch.id)
            .order_by(func.count(Booking.id).desc(), Branch.name)
        )
    ).first()
    return row[0] if row else None


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

    rows: list[UserStat] = []
    for u in users:
        confirmed = Booking.status == BookingStatus.CONFIRMED
        agg = (
            await session.execute(
                select(
                    func.count(Booking.id),
                    func.coalesce(func.sum(Booking.people_count), 0),
                    func.max(Booking.date),
                ).where(Booking.user_id == u.telegram_id, confirmed)
            )
        ).first()
        count, people, last = agg[0], int(agg[1]), agg[2]
        fav = await _favorite_branch(session, u.telegram_id)
        rows.append(
            UserStat(
                name=u.full_name,
                phone=u.phone,
                bookings=count,
                people=people,
                first_seen=u.created_at.date() if u.created_at else None,
                last_booking=last,
                favorite_branch=fav,
            )
        )
    return rows, total_pages
