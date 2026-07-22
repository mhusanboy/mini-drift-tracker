"""Registered-customer listing for the admin panel."""
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User

PER_PAGE = 5


async def count_users(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(User))).scalar_one()


async def users_page(
    session: AsyncSession, page: int, per_page: int = PER_PAGE
) -> tuple[list[User], int, int]:
    """One page of users, oldest first. Returns (users, page, total_pages) with
    ``page`` clamped into range so an out-of-date button can't 404."""
    total = await count_users(session)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))
    result = await session.execute(
        select(User).order_by(User.created_at, User.telegram_id)
        .limit(per_page).offset((page - 1) * per_page)
    )
    return list(result.scalars().all()), page, total_pages
