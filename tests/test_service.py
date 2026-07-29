import pytest
from sqlalchemy import func, select

from bot.db.models import Service
from bot.services import service


@pytest.mark.parametrize("raw,expected", [
    ("@minidriftuz", "minidriftuz"),
    ("minidriftuz", "minidriftuz"),
    ("https://t.me/minidriftuz", "minidriftuz"),
    ("http://t.me/minidriftuz", "minidriftuz"),
    ("t.me/minidriftuz/", "minidriftuz"),
    ("  @Mini_Drift1  ", "Mini_Drift1"),
])
def test_normalize_username_accepts(raw, expected):
    assert service.normalize_username(raw) == expected


@pytest.mark.parametrize("raw", [
    "",            # empty
    "abc",         # too short
    "x" * 33,      # too long
    "@1driftuz",   # must start with a letter
    "drift uz",    # no spaces
    "@drift-uz",   # no dashes
    "миниdrift",   # ascii only
])
def test_normalize_username_rejects(raw):
    assert service.normalize_username(raw) is None


def test_has_location_handles_missing_service():
    assert service.has_location(None) is False
    assert service.has_location(Service(id=1)) is False


def test_has_location_accepts_either_shape():
    assert service.has_location(Service(id=1, latitude=41.3, longitude=69.2)) is True
    assert service.has_location(Service(id=1, location_url="https://maps.example")) is True


async def _count(session_factory) -> int:
    async with session_factory() as s:
        return (await s.execute(select(func.count()).select_from(Service))).scalar_one()


async def test_edits_reuse_a_single_row(session_factory):
    async with session_factory() as s:
        await service.set_price(s, "50 000 so'm")
    async with session_factory() as s:
        await service.set_booking_username(s, "minidriftuz")
    async with session_factory() as s:
        await service.set_price(s, "60 000 so'm")

    assert await _count(session_factory) == 1
    async with session_factory() as s:
        svc = await service.get_service(s)
    # A later edit to one field leaves the others intact.
    assert svc.price_text == "60 000 so'm"
    assert svc.booking_username == "minidriftuz"


async def test_set_hours_round_trips(session_factory):
    async with session_factory() as s:
        await service.set_hours(s, open_hour=11, open_minute=30, close_hour=23, close_minute=0)
    async with session_factory() as s:
        svc = await service.get_service(s)
    assert (svc.open_hour, svc.open_minute) == (11, 30)
    assert (svc.close_hour, svc.close_minute) == (23, 0)


async def test_set_location_replaces_the_previous_one(session_factory):
    async with session_factory() as s:
        await service.set_location(s, latitude=41.3, longitude=69.2, title="Kart", address="X")
    async with session_factory() as s:
        await service.set_location(s, location_url="https://yandex.uz/maps/-/abc")

    async with session_factory() as s:
        svc = await service.get_service(s)
    # Switching from a pin to a link must not leave a stale pin behind.
    assert svc.latitude is None and svc.longitude is None and svc.title is None
    assert svc.location_url == "https://yandex.uz/maps/-/abc"


async def test_get_service_is_none_before_anything_is_set(session_factory):
    async with session_factory() as s:
        assert await service.get_service(s) is None
