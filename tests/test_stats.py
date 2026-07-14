from datetime import date

from bot.db.models import Branch, User
from bot.services import slots, stats


async def _seed(session_factory):
    async with session_factory() as s:
        s.add_all([
            User(telegram_id=1, full_name="Anvar", phone="+1"),
            User(telegram_id=2, full_name="Bek", phone="+2"),
            Branch(id=1, name="Main", address="X", open_hour=10, close_hour=22),
            Branch(id=2, name="North", address="Y", open_hour=10, close_hour=22),
        ])
        await s.commit()
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 13), 10, 3)
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 11, 2)
        await slots.create_booking(s, 1, 2, date(2026, 7, 21), 12, 1)
        await slots.create_booking(s, 2, 2, date(2026, 7, 13), 15, 4)


async def test_overview(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        ov = await stats.overview(s, date(2026, 7, 13))
        assert ov["users"] == 2
        assert ov["bookings"] == 4
        assert ov["today"] == 2
        assert dict(ov["by_branch"]) == {"Main": 2, "North": 2}


async def test_user_stats(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        rows, pages = await stats.user_stats_page(s, page=1, per_page=5)
        assert pages == 1
        anvar = next(r for r in rows if r.name == "Anvar")
        assert anvar.bookings == 3
        assert anvar.people == 6
        assert anvar.last_booking == date(2026, 7, 21)
        # Anvar has 2 bookings at Main, 1 at North -> favorite Main
        assert anvar.favorite_branch == "Main"
