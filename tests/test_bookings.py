from datetime import date

from bot.db.models import BookingStatus, User
from bot.services import bookings

DAY = date(2026, 7, 20)


async def _user(session_factory, uid=1):
    async with session_factory() as s:
        user = User(telegram_id=uid, full_name="Anvar", phone="+998901234567")
        s.add(user)
        await s.commit()
    async with session_factory() as s:
        return await s.get(User, uid)


async def test_create_snapshots_the_customer_and_derives_duration(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "ertaga 18:00", 8, DAY, 18 * 60)
    assert booking.full_name == "Anvar" and booking.phone == "+998901234567"
    assert booking.when_text == "ertaga 18:00"
    assert booking.duration_hours == 2          # ceil(8 / 6)
    assert booking.status == BookingStatus.PENDING
    assert booking.duration_overridden is False


async def test_create_keeps_an_unparsed_request(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "shanba kechqurun", 3, None, None)
    # The request still exists — it just holds no time yet.
    assert booking.date is None and booking.start_minute is None
    assert booking.when_text == "shanba kechqurun"


async def test_set_people_recalculates_duration(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "18:00", 5, DAY, 18 * 60)
    assert booking.duration_hours == 1
    async with session_factory() as s:
        booking = await bookings.set_people(s, booking.id, 10)
    assert booking.duration_hours == 2


async def test_a_hand_set_duration_survives_a_people_edit(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "18:00", 5, DAY, 18 * 60)
    async with session_factory() as s:
        booking = await bookings.set_duration(s, booking.id, 4)
    assert booking.duration_overridden is True
    async with session_factory() as s:
        booking = await bookings.set_people(s, booking.id, 10)
    # 10 people would imply 2h, but the admin said 4 — their word stands.
    assert booking.duration_hours == 4
    assert booking.people_count == 10


async def test_set_time_fills_in_an_unparsed_request(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "kechqurun", 2, None, None)
    async with session_factory() as s:
        booking = await bookings.set_time(s, booking.id, DAY, 19 * 60 + 30)
    assert booking.date == DAY and booking.start_minute == 19 * 60 + 30


async def test_set_status_stamps_the_decision(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        booking = await bookings.create(s, user, "18:00", 2, DAY, 18 * 60)
    assert booking.decided_at is None
    async with session_factory() as s:
        booking = await bookings.set_status(s, booking.id, BookingStatus.ACCEPTED)
    assert booking.status == BookingStatus.ACCEPTED
    assert booking.decided_at is not None


async def test_edits_to_a_missing_booking_return_none(session_factory):
    async with session_factory() as s:
        assert await bookings.get(s, 404) is None
        assert await bookings.set_people(s, 404, 3) is None
        assert await bookings.set_duration(s, 404, 3) is None
        assert await bookings.set_time(s, 404, DAY, 600) is None
        assert await bookings.set_status(s, 404, BookingStatus.ACCEPTED) is None


async def test_history_is_newest_first(session_factory):
    user = await _user(session_factory)
    async with session_factory() as s:
        await bookings.create(s, user, "first", 2, DAY, 18 * 60)
        await bookings.create(s, user, "second", 2, DAY, 19 * 60)
    async with session_factory() as s:
        rows = await bookings.history(s)
    assert [b.when_text for b in rows] == ["second", "first"]
