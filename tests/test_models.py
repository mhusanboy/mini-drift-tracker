from bot.db.models import PHOTO, Promo, Service, User


async def test_insert_and_read_user(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="Anvar Anvarov", phone="+998901234567", language="uz"))
        await s.commit()
    async with session_factory() as s:
        u = await s.get(User, 1)
    assert u.full_name == "Anvar Anvarov"
    assert u.language == "uz"
    assert u.created_at is not None


async def test_user_language_defaults_to_ru(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=2, full_name="A", phone="+998"))
        await s.commit()
    async with session_factory() as s:
        assert (await s.get(User, 2)).language == "ru"


async def test_service_stores_a_pin_or_a_link(session_factory):
    async with session_factory() as s:
        s.add(Service(id=1, price_text="50 000", booking_username="minidriftuz",
                      title="Mini Drift", address="Tashkent",
                      latitude=41.311081, longitude=69.240562))
        await s.commit()
    async with session_factory() as s:
        svc = await s.get(Service, 1)
    assert round(svc.latitude, 4) == 41.3111
    assert svc.location_url is None
    assert svc.booking_username == "minidriftuz"


async def test_service_fields_start_empty(session_factory):
    async with session_factory() as s:
        s.add(Service(id=1))
        await s.commit()
    async with session_factory() as s:
        svc = await s.get(Service, 1)
    assert svc.price_text is None and svc.booking_username is None
    assert svc.latitude is None and svc.location_url is None


async def test_promo_media_is_optional(session_factory):
    async with session_factory() as s:
        s.add(Promo(id=1, text="Text only"))
        s.add(Promo(id=2, text="With photo", media_type=PHOTO, file_id="f-1"))
        await s.commit()
    async with session_factory() as s:
        plain, withmedia = await s.get(Promo, 1), await s.get(Promo, 2)
    assert plain.media_type is None and plain.file_id is None
    assert withmedia.media_type == PHOTO and withmedia.file_id == "f-1"
