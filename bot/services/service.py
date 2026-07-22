"""The single configurable service row: prices, location, booking username."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Service

SERVICE_ID = 1


async def get_service(session: AsyncSession) -> Service | None:
    return (
        await session.execute(select(Service).order_by(Service.id).limit(1))
    ).scalar_one_or_none()


async def _get_or_create(session: AsyncSession) -> Service:
    service = await get_service(session)
    if service is None:
        service = Service(id=SERVICE_ID)
        session.add(service)
    return service


async def set_price(session: AsyncSession, text: str) -> Service:
    service = await _get_or_create(session)
    service.price_text = text
    await session.commit()
    await session.refresh(service)
    return service


async def set_booking_username(session: AsyncSession, username: str) -> Service:
    service = await _get_or_create(session)
    service.booking_username = username
    await session.commit()
    await session.refresh(service)
    return service


async def set_hours(
    session: AsyncSession, *, open_hour, open_minute, close_hour, close_minute,
) -> Service:
    service = await _get_or_create(session)
    service.open_hour = open_hour
    service.open_minute = open_minute
    service.close_hour = close_hour
    service.close_minute = close_minute
    await session.commit()
    await session.refresh(service)
    return service


async def set_location(
    session: AsyncSession, *, title=None, address=None,
    latitude=None, longitude=None, location_url=None,
) -> Service:
    """Replace the location wholesale — a new one always supersedes the old."""
    service = await _get_or_create(session)
    service.title = title
    service.address = address
    service.latitude = latitude
    service.longitude = longitude
    service.location_url = location_url
    await session.commit()
    await session.refresh(service)
    return service


def has_location(service: Service | None) -> bool:
    if service is None:
        return False
    return (service.latitude is not None and service.longitude is not None) or bool(
        service.location_url
    )


def normalize_username(text: str) -> str | None:
    """Accept ``@name``, ``name`` or a t.me link; return the bare username.

    Telegram usernames are 5-32 chars of ``[A-Za-z0-9_]`` and must start with a
    letter. Returns ``None`` if the text is not a usable username.
    """
    name = text.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):]
            break
    name = name.strip().strip("/")
    if not 5 <= len(name) <= 32:
        return None
    if not name[0].isalpha():
        return None
    if not all(c.isascii() and (c.isalnum() or c == "_") for c in name):
        return None
    return name
