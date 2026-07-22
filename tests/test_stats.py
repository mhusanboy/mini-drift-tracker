from datetime import date

from bot.db.models import Booking, BookingStatus, User
from bot.services import stats

TODAY = date(2026, 7, 20)


async def _seed(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="Anvar", phone="+1", language="uz"))
        s.add(User(telegram_id=2, full_name="Bek", phone="+2", language="ru"))
        # Anvar: one accepted today (4 people, 1h), one rejected, one pending.
        s.add(Booking(user_id=1, full_name="Anvar", phone="+1", date=TODAY,
                      start_minute=660, people_count=4, duration_hours=1,
                      status=BookingStatus.ACCEPTED))
        s.add(Booking(user_id=1, full_name="Anvar", phone="+1", date=TODAY,
                      start_minute=720, people_count=2, duration_hours=1,
                      status=BookingStatus.REJECTED))
        s.add(Booking(user_id=1, full_name="Anvar", phone="+1", date=TODAY,
                      start_minute=780, people_count=2, duration_hours=1,
                      status=BookingStatus.PENDING))
        # Bek: one accepted tomorrow (9 people, 2h).
        s.add(Booking(user_id=2, full_name="Bek", phone="+2",
                      date=date(2026, 7, 21), start_minute=660, people_count=9,
                      duration_hours=2, status=BookingStatus.ACCEPTED))
        await s.commit()


async def test_overview_counts_each_status(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        ov = await stats.overview(s, TODAY)
    assert ov["users"] == 2
    assert ov["requests"] == 4
    assert ov["accepted"] == 2
    assert ov["rejected"] == 1
    assert ov["pending"] == 1
    assert ov["today"] == 1          # only Anvar's accepted one is today
    assert ov["people"] == 13        # 4 + 9, accepted only
    assert ov["hours"] == 3          # 1 + 2, accepted only


async def test_overview_on_an_empty_database(session_factory):
    async with session_factory() as s:
        ov = await stats.overview(s, TODAY)
    assert ov["requests"] == 0 and ov["people"] == 0 and ov["hours"] == 0


async def test_user_stats_separate_requests_from_accepted(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        rows = await stats.all_user_stats(s)
    anvar, bek = rows
    assert (anvar.requests, anvar.accepted, anvar.people) == (3, 1, 4)
    assert (bek.requests, bek.accepted, bek.people) == (1, 1, 9)
    assert anvar.last_booking == TODAY
    assert bek.last_booking == date(2026, 7, 21)


async def test_user_with_no_bookings_is_still_listed(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=9, full_name="Yangi", phone="+9"))
        await s.commit()
    async with session_factory() as s:
        row = (await stats.all_user_stats(s))[0]
    assert row.requests == 0 and row.people == 0 and row.last_booking is None
