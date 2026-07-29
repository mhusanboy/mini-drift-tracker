from bot.db.models import User
from bot.services import users


async def _add(session_factory, count: int) -> None:
    async with session_factory() as s:
        for i in range(1, count + 1):
            s.add(User(telegram_id=i, full_name=f"User {i}", phone=f"+99890000000{i}"))
        await s.commit()


async def test_empty(session_factory):
    async with session_factory() as s:
        rows, page, pages = await users.users_page(s, 1)
    assert rows == [] and page == 1 and pages == 1


async def test_pages_split_by_per_page(session_factory):
    await _add(session_factory, 7)
    async with session_factory() as s:
        first, page, pages = await users.users_page(s, 1, per_page=5)
        second, _, _ = await users.users_page(s, 2, per_page=5)
    assert (page, pages) == (1, 2)
    assert len(first) == 5 and len(second) == 2
    # Oldest first, and no user appears on two pages.
    assert [u.telegram_id for u in first] == [1, 2, 3, 4, 5]
    assert [u.telegram_id for u in second] == [6, 7]


async def test_page_is_clamped_into_range(session_factory):
    await _add(session_factory, 7)
    async with session_factory() as s:
        _, high, pages = await users.users_page(s, 99, per_page=5)
        _, low, _ = await users.users_page(s, 0, per_page=5)
    assert high == pages == 2
    assert low == 1


async def test_count_users(session_factory):
    await _add(session_factory, 3)
    async with session_factory() as s:
        assert await users.count_users(s) == 3
