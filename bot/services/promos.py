"""Aksiyalar — the admin-managed list of discounts."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Promo


async def list_promos(session: AsyncSession) -> list[Promo]:
    """Newest first — a fresh aksiya is the one customers should see on top."""
    result = await session.execute(select(Promo).order_by(Promo.id.desc()))
    return list(result.scalars().all())


async def add_promo(
    session: AsyncSession, text: str, media_type: str | None = None,
    file_id: str | None = None,
) -> Promo:
    promo = Promo(text=text, media_type=media_type, file_id=file_id)
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def delete_promo(session: AsyncSession, promo_id: int) -> bool:
    promo = await session.get(Promo, promo_id)
    if promo is None:
        return False
    await session.delete(promo)
    await session.commit()
    return True
