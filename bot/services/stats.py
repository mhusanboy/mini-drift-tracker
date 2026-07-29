"""Aggregates for the admin's stats screen and the Excel export."""
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Booking, BookingStatus, User


@dataclass
class UserStat:
    name: str
    phone: str
    language: str
    requests: int
    accepted: int
    people: int
    first_seen: date | None
    last_booking: date | None


async def _count(session: AsyncSession, *where) -> int:
    return (
        await session.execute(select(func.count()).select_from(Booking).where(*where))
    ).scalar_one()


async def overview(session: AsyncSession, today: date) -> dict:
    accepted = Booking.status == BookingStatus.ACCEPTED
    people = (
        await session.execute(
            select(func.coalesce(func.sum(Booking.people_count), 0)).where(accepted)
        )
    ).scalar_one()
    hours = (
        await session.execute(
            select(func.coalesce(func.sum(Booking.duration_hours), 0)).where(accepted)
        )
    ).scalar_one()
    return {
        "users": (await session.execute(select(func.count()).select_from(User))).scalar_one(),
        "requests": await _count(session),
        "accepted": await _count(session, accepted),
        "rejected": await _count(session, Booking.status == BookingStatus.REJECTED),
        "pending": await _count(session, Booking.status == BookingStatus.PENDING),
        "today": await _count(session, accepted, Booking.date == today),
        "people": int(people),
        "hours": int(hours),
    }


async def _user_stat(session: AsyncSession, user: User) -> UserStat:
    accepted = Booking.status == BookingStatus.ACCEPTED
    requests = await _count(session, Booking.user_id == user.telegram_id)
    accepted_count = await _count(session, Booking.user_id == user.telegram_id, accepted)
    agg = (
        await session.execute(
            select(
                func.coalesce(func.sum(Booking.people_count), 0),
                func.max(Booking.date),
            ).where(Booking.user_id == user.telegram_id, accepted)
        )
    ).first()
    return UserStat(
        name=user.full_name,
        phone=user.phone,
        language=user.language,
        requests=requests,
        accepted=accepted_count,
        people=int(agg[0]),
        first_seen=user.created_at.date() if user.created_at else None,
        last_booking=agg[1],
    )


async def all_user_stats(session: AsyncSession) -> list[UserStat]:
    users = (
        await session.execute(select(User).order_by(User.created_at, User.telegram_id))
    ).scalars().all()
    return [await _user_stat(session, u) for u in users]
