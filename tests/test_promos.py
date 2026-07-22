from bot.db.models import PHOTO, VIDEO
from bot.services import promos


async def test_add_and_list_newest_first(session_factory):
    async with session_factory() as s:
        await promos.add_promo(s, "Birinchi aksiya")
        await promos.add_promo(s, "Ikkinchi aksiya", PHOTO, "file-123")
    async with session_factory() as s:
        items = await promos.list_promos(s)
    assert [p.text for p in items] == ["Ikkinchi aksiya", "Birinchi aksiya"]
    assert items[0].media_type == PHOTO and items[0].file_id == "file-123"


async def test_media_is_optional(session_factory):
    async with session_factory() as s:
        promo = await promos.add_promo(s, "Matn xolos")
    assert promo.media_type is None and promo.file_id is None


async def test_video_promo_round_trips(session_factory):
    async with session_factory() as s:
        await promos.add_promo(s, "Video aksiya", VIDEO, "vid-9")
    async with session_factory() as s:
        promo = (await promos.list_promos(s))[0]
    assert promo.media_type == VIDEO and promo.file_id == "vid-9"


async def test_delete_removes_only_that_promo(session_factory):
    async with session_factory() as s:
        keep = await promos.add_promo(s, "Qoladi")
        drop = await promos.add_promo(s, "O'chadi")
    async with session_factory() as s:
        assert await promos.delete_promo(s, drop.id) is True
    async with session_factory() as s:
        items = await promos.list_promos(s)
    assert [p.id for p in items] == [keep.id]


async def test_delete_unknown_promo_is_false(session_factory):
    async with session_factory() as s:
        assert await promos.delete_promo(s, 404) is False
