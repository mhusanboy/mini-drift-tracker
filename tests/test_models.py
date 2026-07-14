from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from bot.db.models import Booking, BookingStatus, Branch, User


async def test_insert_and_read_user(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="Anvar Anvarov", phone="+998901234567", language="uz"))
        await s.commit()
    async with session_factory() as s:
        u = await s.get(User, 1)
        assert u.full_name == "Anvar Anvarov"
        assert u.language == "uz"


async def test_confirmed_slot_is_unique(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=10, close_hour=22))
        await s.commit()
        s.add(Booking(user_id=1, branch_id=1, date=date(2026, 7, 20), start_hour=10, people_count=2))
        await s.commit()
        s.add(Booking(user_id=1, branch_id=1, date=date(2026, 7, 20), start_hour=10, people_count=3))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_cancelled_does_not_block_rebooking(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=10, close_hour=22))
        await s.commit()
        s.add(Booking(user_id=1, branch_id=1, date=date(2026, 7, 20), start_hour=10,
                      people_count=2, status=BookingStatus.CANCELLED))
        await s.commit()
        # A confirmed booking on the same slot must succeed.
        s.add(Booking(user_id=1, branch_id=1, date=date(2026, 7, 20), start_hour=10, people_count=2))
        await s.commit()
        assert True
