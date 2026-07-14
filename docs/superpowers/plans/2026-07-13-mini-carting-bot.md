# Mini Carting Booking Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bilingual (ru/uz) Telegram bot for a Tashkent go-kart service where customers register and book hourly slots, and admins get notified and view analytics + manage branches.

**Architecture:** aiogram 3.x async bot with Router-based handlers. Business logic lives in a tested `services/` layer (pure-ish functions over an async SQLAlchemy session); handlers are thin adapters. SQLite via SQLAlchemy 2.0 async. Slots are computed on the fly from branch open/close hours minus confirmed bookings — no materialized slot rows. A partial unique index on confirmed bookings prevents double-booking.

**Tech Stack:** Python 3.11+, aiogram 3.x, SQLAlchemy 2.0 (async) + aiosqlite, pydantic-settings, pytest + pytest-asyncio.

## Global Constraints

- Python **3.11+** (uses `datetime`, `date`, modern typing).
- UI languages: **Russian (`ru`)** and **Uzbek Latin (`uz`)** only; every user-facing string goes through `t(key, lang, **kwargs)` — no hard-coded user-facing text in handlers.
- Time granularity: **whole hours only**, on the hour.
- Day picker: **next 7 days including today**.
- Slot occupancy: **one group per (branch, date, hour)**; `people_count` is informational (≥ 1).
- Admins identified by Telegram user id in `ADMIN_IDS`.
- Phone captured via **Share-contact button only** — typed phone numbers are rejected.
- All DB access is **async** (`AsyncSession`); never block the event loop.

---

### Task 1: Project scaffolding & config

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `bot/__init__.py` (empty)
- Create: `bot/config.py`
- Create: `tests/__init__.py` (empty)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings) with fields `bot_token: str`, `admin_ids: list[int]`, `db_path: str`. Module-level `get_settings() -> Settings` (cached). Helper `Settings.is_admin(user_id: int) -> bool`.

- [ ] **Step 1: Create `requirements.txt`**

```
aiogram==3.13.1
SQLAlchemy==2.0.35
aiosqlite==0.20.0
pydantic-settings==2.5.2
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
venv/
.env
*.db
.pytest_cache/
```

- [ ] **Step 3: Create `.env.example`**

```
BOT_TOKEN=123456:replace-with-token-from-botfather
ADMIN_IDS=111111111,222222222
DB_PATH=carting.db
```

- [ ] **Step 4: Write the failing test** — `tests/test_config.py`

```python
from bot.config import Settings


def test_admin_ids_parsed_from_csv():
    s = Settings(bot_token="t", admin_ids="111,222", db_path="x.db")
    assert s.admin_ids == [111, 222]
    assert s.is_admin(111) is True
    assert s.is_admin(999) is False


def test_admin_ids_accepts_list():
    s = Settings(bot_token="t", admin_ids=[5], db_path="x.db")
    assert s.admin_ids == [5]
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.config'`)

- [ ] **Step 6: Create `bot/config.py`**

```python
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    admin_ids: list[int] = []
    db_path: str = "carting.db"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip()]
        return v

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: Initialize git and commit**

```bash
git init
git add requirements.txt .gitignore .env.example bot/ tests/ docs/
git commit -m "chore: scaffold project, config, and design docs"
```

---

### Task 2: Database base & models

**Files:**
- Create: `bot/db/__init__.py` (empty)
- Create: `bot/db/base.py`
- Create: `bot/db/models.py`
- Test: `tests/conftest.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Base` (DeclarativeBase).
  - Models `User(telegram_id, full_name, phone, language, created_at)`, `Branch(id, name, address, open_hour, close_hour, is_active, created_at)`, `Booking(id, user_id, branch_id, date, start_hour, people_count, status, created_at)`.
  - `BookingStatus` constants: `CONFIRMED = "confirmed"`, `CANCELLED = "cancelled"`.
  - `make_engine(db_path: str) -> AsyncEngine`, `make_session_factory(engine) -> async_sessionmaker[AsyncSession]`, `async def init_db(engine) -> None` (runs `create_all`).
  - A **partial unique index** `uq_booking_confirmed_slot` on `(branch_id, date, start_hour)` where `status = 'confirmed'`.

- [ ] **Step 1: Create `bot/db/base.py`**

```python
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(db_path: str) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    # Import models so they register on Base.metadata before create_all.
    from bot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Create `bot/db/models.py`**

```python
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class BookingStatus:
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False, default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    open_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    close_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="branch")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=BookingStatus.CONFIRMED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="bookings")
    branch: Mapped["Branch"] = relationship(back_populates="bookings")

    __table_args__ = (
        Index(
            "uq_booking_confirmed_slot",
            "branch_id",
            "date",
            "start_hour",
            unique=True,
            sqlite_where=text("status = 'confirmed'"),
        ),
    )
```

- [ ] **Step 3: Create `tests/conftest.py`** (shared async in-memory DB fixture)

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from bot.db.base import Base, make_session_factory


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    from bot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()
```

Also add to `tests/` a `pytest.ini` at repo root:

- [ ] **Step 4: Create `pytest.ini`** (repo root)

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Write the failing test** — `tests/test_models.py`

```python
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
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL (module/models not present yet, or import error resolved then assertion runs)

- [ ] **Step 7: Confirm implementation from Steps 1-2 makes tests pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS (3 passed). If the partial-index test fails, verify the index uses `sqlite_where=text("status = 'confirmed'")` — SQLite renders this as a partial unique index so cancelled rows don't block rebooking.

- [ ] **Step 8: Commit**

```bash
git add bot/db/ tests/conftest.py tests/test_models.py pytest.ini
git commit -m "feat: add SQLAlchemy models with partial-unique confirmed-slot index"
```

---

### Task 3: i18n locales

**Files:**
- Create: `bot/locales.py`
- Test: `tests/test_locales.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `t(key: str, lang: str, **kwargs) -> str` — returns the localized string, `.format(**kwargs)` applied. Falls back to `ru` if `lang` unknown, and returns the key itself if the key is missing. `LANGUAGES = {"ru": "Русский", "uz": "O'zbekcha"}`.

- [ ] **Step 1: Write the failing test** — `tests/test_locales.py`

```python
from bot.locales import LANGUAGES, t


def test_returns_localized_string():
    assert t("choose_language", "ru") != t("choose_language", "uz")


def test_formatting_kwargs():
    msg = t("booking_confirmed", "ru", branch="Main", date="2026-07-20", hour=10)
    assert "Main" in msg and "10" in msg


def test_unknown_lang_falls_back_to_ru():
    assert t("main_menu_title", "de") == t("main_menu_title", "ru")


def test_missing_key_returns_key():
    assert t("__nope__", "ru") == "__nope__"


def test_languages_map():
    assert set(LANGUAGES) == {"ru", "uz"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_locales.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.locales'`)

- [ ] **Step 3: Create `bot/locales.py`**

Provide the full string table. Keys below are the complete set used by all handlers — add every one.

```python
LANGUAGES = {"ru": "Русский", "uz": "O'zbekcha"}

_STRINGS = {
    "ru": {
        "choose_language": "Выберите язык:",
        "ask_full_name": "Введите ваше полное имя (например, Анвар Анваров):",
        "ask_phone": "Поделитесь номером телефона, нажав кнопку ниже.",
        "share_phone_button": "📱 Поделиться номером",
        "phone_use_button": "Пожалуйста, используйте кнопку ниже, чтобы поделиться номером.",
        "registered": "Готово! Добро пожаловать, {name}.",
        "main_menu_title": "Главное меню",
        "btn_book": "🏁 Забронировать",
        "btn_my_bookings": "📋 Мои брони",
        "btn_language": "🌐 Язык",
        "choose_branch": "Выберите филиал:",
        "no_branches": "Пока нет доступных филиалов. Загляните позже.",
        "choose_day": "Выберите день:",
        "choose_time": "Выберите время начала:",
        "no_slots": "На этот день нет свободных слотов. Выберите другой день.",
        "ask_people": "Сколько человек придёт? Введите число:",
        "people_invalid": "Введите положительное целое число.",
        "confirm_title": "Подтвердите бронь:\n\nФилиал: {branch}\nДата: {date}\nВремя: {hour}:00\nЛюдей: {people}",
        "btn_confirm": "✅ Подтвердить",
        "btn_cancel": "❌ Отмена",
        "booking_confirmed": "✅ Бронь подтверждена!\n{branch}, {date} в {hour}:00.",
        "booking_cancelled_user": "Бронь отменена.",
        "slot_taken": "Упс, это время только что заняли. Выберите другое.",
        "cancelled_flow": "Отменено.",
        "my_bookings_empty": "У вас нет предстоящих броней.",
        "my_bookings_title": "Ваши предстоящие брони:",
        "booking_line": "{branch} — {date} в {hour}:00 ({people} чел.)",
        "btn_cancel_booking": "❌ Отменить {date} {hour}:00",
        "back": "⬅️ Назад",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        # admin
        "not_authorized": "Команда доступна только администраторам.",
        "admin_new_booking": "🆕 Новая бронь\nФилиал: {branch}\nДата: {date} {hour}:00\nЛюдей: {people}\nКлиент: {name}\nТел: {phone}",
        "admin_cancelled": "🚫 Отмена брони\nФилиал: {branch}\nДата: {date} {hour}:00\nКлиент: {name}\nТел: {phone}",
        "stats_overview": "📊 Статистика\nПользователей: {users}\nБроней (всего): {bookings}\nБроней сегодня: {today}\n\nПо филиалам:\n{by_branch}",
        "stats_branch_line": "• {name}: {count}",
        "users_header": "👥 Пользователи (стр. {page}/{pages})",
        "user_card": "{name} | {phone}\nБроней: {bookings}, людей: {people}\nВпервые: {first}, последняя: {last}\nЛюбимый филиал: {fav}",
        "branches_title": "🏢 Филиалы:",
        "branch_admin_line": "{status} {name} ({open}:00–{close}:00) — {address}",
        "btn_add_branch": "➕ Добавить филиал",
        "btn_edit": "✏️ {name}",
        "btn_toggle_active": "🔀 переключить",
        "ask_branch_name": "Название филиала:",
        "ask_branch_address": "Адрес:",
        "ask_open_hour": "Час открытия (0–23):",
        "ask_close_hour": "Час закрытия (1–24, больше часа открытия):",
        "hour_invalid": "Введите корректный час.",
        "branch_saved": "Филиал сохранён.",
        "branch_toggled": "Филиал обновлён.",
    },
    "uz": {
        "choose_language": "Tilni tanlang:",
        "ask_full_name": "To'liq ismingizni kiriting (masalan, Anvar Anvarov):",
        "ask_phone": "Quyidagi tugma orqali telefon raqamingizni yuboring.",
        "share_phone_button": "📱 Raqamni yuborish",
        "phone_use_button": "Iltimos, raqamni yuborish uchun pastdagi tugmadan foydalaning.",
        "registered": "Tayyor! Xush kelibsiz, {name}.",
        "main_menu_title": "Asosiy menyu",
        "btn_book": "🏁 Band qilish",
        "btn_my_bookings": "📋 Mening bronlarim",
        "btn_language": "🌐 Til",
        "choose_branch": "Filialni tanlang:",
        "no_branches": "Hozircha mavjud filial yo'q. Keyinroq qarang.",
        "choose_day": "Kunni tanlang:",
        "choose_time": "Boshlanish vaqtini tanlang:",
        "no_slots": "Bu kunda bo'sh vaqt yo'q. Boshqa kunni tanlang.",
        "ask_people": "Necha kishi keladi? Sonini kiriting:",
        "people_invalid": "Musbat butun son kiriting.",
        "confirm_title": "Bronni tasdiqlang:\n\nFilial: {branch}\nSana: {date}\nVaqt: {hour}:00\nKishi: {people}",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_cancel": "❌ Bekor qilish",
        "booking_confirmed": "✅ Bron tasdiqlandi!\n{branch}, {date} soat {hour}:00.",
        "booking_cancelled_user": "Bron bekor qilindi.",
        "slot_taken": "Afsus, bu vaqt hozirgina band qilindi. Boshqasini tanlang.",
        "cancelled_flow": "Bekor qilindi.",
        "my_bookings_empty": "Sizda kelgusi bronlar yo'q.",
        "my_bookings_title": "Kelgusi bronlaringiz:",
        "booking_line": "{branch} — {date} soat {hour}:00 ({people} kishi)",
        "btn_cancel_booking": "❌ Bekor: {date} {hour}:00",
        "back": "⬅️ Orqaga",
        "today": "Bugun",
        "tomorrow": "Ertaga",
        # admin
        "not_authorized": "Bu buyruq faqat adminlar uchun.",
        "admin_new_booking": "🆕 Yangi bron\nFilial: {branch}\nSana: {date} {hour}:00\nKishi: {people}\nMijoz: {name}\nTel: {phone}",
        "admin_cancelled": "🚫 Bron bekor qilindi\nFilial: {branch}\nSana: {date} {hour}:00\nMijoz: {name}\nTel: {phone}",
        "stats_overview": "📊 Statistika\nFoydalanuvchilar: {users}\nBronlar (jami): {bookings}\nBugungi bronlar: {today}\n\nFiliallar bo'yicha:\n{by_branch}",
        "stats_branch_line": "• {name}: {count}",
        "users_header": "👥 Foydalanuvchilar ({page}/{pages}-sahifa)",
        "user_card": "{name} | {phone}\nBronlar: {bookings}, kishi: {people}\nBirinchi: {first}, oxirgi: {last}\nSevimli filial: {fav}",
        "branches_title": "🏢 Filiallar:",
        "branch_admin_line": "{status} {name} ({open}:00–{close}:00) — {address}",
        "btn_add_branch": "➕ Filial qo'shish",
        "btn_edit": "✏️ {name}",
        "btn_toggle_active": "🔀 o'zgartirish",
        "ask_branch_name": "Filial nomi:",
        "ask_branch_address": "Manzil:",
        "ask_open_hour": "Ochilish soati (0–23):",
        "ask_close_hour": "Yopilish soati (1–24, ochilishdan katta):",
        "hour_invalid": "To'g'ri soat kiriting.",
        "branch_saved": "Filial saqlandi.",
        "branch_toggled": "Filial yangilandi.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    table = _STRINGS.get(lang, _STRINGS["ru"])
    template = table.get(key)
    if template is None:
        template = _STRINGS["ru"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_locales.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add bot/locales.py tests/test_locales.py
git commit -m "feat: add ru/uz i18n string table and t() helper"
```

---

### Task 4: Slots service (availability + booking create/cancel)

**Files:**
- Create: `bot/services/__init__.py` (empty)
- Create: `bot/services/slots.py`
- Test: `tests/test_slots.py`

**Interfaces:**
- Consumes: models from Task 2.
- Produces (all async, take `session: AsyncSession`):
  - `next_days(today: date, count: int = 7) -> list[date]` (pure, not async).
  - `async list_active_branches(session) -> list[Branch]`.
  - `async get_branch(session, branch_id) -> Branch | None`.
  - `async free_hours(session, branch, day, now: datetime) -> list[int]` — candidate hours `range(open_hour, close_hour)` minus confirmed-booked hours, minus past hours when `day == now.date()`.
  - `async create_booking(session, user_id, branch_id, day, hour, people) -> Booking | None` — returns the Booking, or `None` if the slot is already taken (IntegrityError rolled back).
  - `async cancel_booking(session, booking_id, user_id) -> Booking | None` — sets status to cancelled if the booking belongs to the user and is confirmed; returns it (with `branch` loaded) or `None`.
  - `async upcoming_bookings(session, user_id, now: datetime) -> list[Booking]` — confirmed bookings at or after `now`, `branch` eager-loaded, sorted by (date, hour).

- [ ] **Step 1: Write the failing tests** — `tests/test_slots.py`

```python
from datetime import date, datetime

from bot.db.models import Booking, BookingStatus, Branch, User
from bot.services import slots


def test_next_days_count_and_start():
    days = slots.next_days(date(2026, 7, 13), 7)
    assert len(days) == 7
    assert days[0] == date(2026, 7, 13)
    assert days[-1] == date(2026, 7, 19)


async def _seed(session_factory):
    async with session_factory() as s:
        s.add(User(telegram_id=1, full_name="A", phone="+1"))
        s.add(Branch(id=1, name="Main", address="X", open_hour=10, close_hour=14, is_active=True))
        s.add(Branch(id=2, name="Old", address="Y", open_hour=9, close_hour=12, is_active=False))
        await s.commit()


async def test_list_active_branches(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        branches = await slots.list_active_branches(s)
        assert [b.id for b in branches] == [1]


async def test_free_hours_full_range_future_day(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [10, 11, 12, 13]


async def test_free_hours_excludes_booked(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 11, 2)
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 20), datetime(2026, 7, 13, 8, 0))
        assert hours == [10, 12, 13]


async def test_free_hours_excludes_past_hours_today(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.get_branch(s, 1)
        hours = await slots.free_hours(s, b, date(2026, 7, 13), datetime(2026, 7, 13, 11, 30))
        assert hours == [12, 13]


async def test_create_booking_double_returns_none(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        first = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        assert first is not None
        second = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 4)
        assert second is None


async def test_cancel_frees_slot_and_allows_rebook(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        cancelled = await slots.cancel_booking(s, b.id, user_id=1)
        assert cancelled.status == BookingStatus.CANCELLED
        again = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 3)
        assert again is not None


async def test_cancel_wrong_user_returns_none(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        b = await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        assert await slots.cancel_booking(s, b.id, user_id=999) is None


async def test_upcoming_bookings_sorted_and_confirmed_only(session_factory):
    await _seed(session_factory)
    async with session_factory() as s:
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 13, 2)
        await slots.create_booking(s, 1, 1, date(2026, 7, 20), 10, 2)
        past = await slots.create_booking(s, 1, 1, date(2026, 7, 12), 10, 2)
        up = await slots.upcoming_bookings(s, 1, datetime(2026, 7, 13, 9, 0))
        assert [(x.date, x.start_hour) for x in up] == [(date(2026, 7, 20), 10), (date(2026, 7, 20), 13)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_slots.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.services.slots'`)

- [ ] **Step 3: Create `bot/services/slots.py`**

```python
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import Booking, BookingStatus, Branch


def next_days(today: date, count: int = 7) -> list[date]:
    return [today + timedelta(days=i) for i in range(count)]


async def list_active_branches(session: AsyncSession) -> list[Branch]:
    result = await session.execute(
        select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name)
    )
    return list(result.scalars().all())


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    return await session.get(Branch, branch_id)


async def free_hours(
    session: AsyncSession, branch: Branch, day: date, now: datetime
) -> list[int]:
    result = await session.execute(
        select(Booking.start_hour).where(
            Booking.branch_id == branch.id,
            Booking.date == day,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booked = set(result.scalars().all())
    hours = []
    for hour in range(branch.open_hour, branch.close_hour):
        if hour in booked:
            continue
        if day == now.date() and hour <= now.hour:
            continue
        hours.append(hour)
    return hours


async def create_booking(
    session: AsyncSession,
    user_id: int,
    branch_id: int,
    day: date,
    hour: int,
    people: int,
) -> Booking | None:
    booking = Booking(
        user_id=user_id,
        branch_id=branch_id,
        date=day,
        start_hour=hour,
        people_count=people,
        status=BookingStatus.CONFIRMED,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return None
    await session.refresh(booking)
    return booking


async def cancel_booking(
    session: AsyncSession, booking_id: int, user_id: int
) -> Booking | None:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.branch))
        .where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        return None
    booking.status = BookingStatus.CANCELLED
    await session.commit()
    return booking


async def upcoming_bookings(
    session: AsyncSession, user_id: int, now: datetime
) -> list[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.branch))
        .where(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
        .order_by(Booking.date, Booking.start_hour)
    )
    out = []
    for b in result.scalars().all():
        booking_dt = datetime(b.date.year, b.date.month, b.date.day, b.start_hour)
        if booking_dt >= now.replace(minute=0, second=0, microsecond=0) or b.date > now.date():
            if b.date > now.date() or b.start_hour >= now.hour:
                out.append(b)
    return out
```

Note on `upcoming_bookings`: keep it simple — a booking is upcoming if `b.date > now.date()`, or `b.date == now.date() and b.start_hour >= now.hour`. Simplify the loop body to exactly that condition:

```python
    out = []
    for b in result.scalars().all():
        if b.date > now.date() or (b.date == now.date() and b.start_hour >= now.hour):
            out.append(b)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_slots.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add bot/services/__init__.py bot/services/slots.py tests/test_slots.py
git commit -m "feat: add slots service with availability and booking lifecycle"
```

---

### Task 5: Stats service

**Files:**
- Create: `bot/services/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Consumes: models from Task 2.
- Produces (async, take `session`):
  - `async overview(session) -> dict` with keys `users:int`, `bookings:int` (confirmed), `today:int` (confirmed booked for `today` arg), `by_branch: list[tuple[str,int]]`. Signature: `overview(session, today: date)`.
  - `async user_stats_page(session, page: int, per_page: int = 5) -> tuple[list[UserStat], int]` returns `(rows, total_pages)`.
  - Dataclass `UserStat(name, phone, bookings, people, first_seen, last_booking, favorite_branch)` where `last_booking` is a `date | None`, `favorite_branch` is `str | None`.

- [ ] **Step 1: Write the failing tests** — `tests/test_stats.py`

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_stats.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.services.stats'`)

- [ ] **Step 3: Create `bot/services/stats.py`**

```python
import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select

from bot.db.models import Booking, BookingStatus, Branch, User
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class UserStat:
    name: str
    phone: str
    bookings: int
    people: int
    first_seen: date
    last_booking: date | None
    favorite_branch: str | None


async def overview(session: AsyncSession, today: date) -> dict:
    users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    confirmed = Booking.status == BookingStatus.CONFIRMED
    bookings = (
        await session.execute(select(func.count()).select_from(Booking).where(confirmed))
    ).scalar_one()
    today_count = (
        await session.execute(
            select(func.count()).select_from(Booking).where(confirmed, Booking.date == today)
        )
    ).scalar_one()
    by_branch_rows = (
        await session.execute(
            select(Branch.name, func.count(Booking.id))
            .join(Booking, Booking.branch_id == Branch.id)
            .where(confirmed)
            .group_by(Branch.id)
            .order_by(Branch.name)
        )
    ).all()
    return {
        "users": users,
        "bookings": bookings,
        "today": today_count,
        "by_branch": [(name, count) for name, count in by_branch_rows],
    }


async def _favorite_branch(session: AsyncSession, user_id: int) -> str | None:
    row = (
        await session.execute(
            select(Branch.name, func.count(Booking.id).label("c"))
            .join(Booking, Booking.branch_id == Branch.id)
            .where(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED)
            .group_by(Branch.id)
            .order_by(func.count(Booking.id).desc(), Branch.name)
        )
    ).first()
    return row[0] if row else None


async def user_stats_page(
    session: AsyncSession, page: int, per_page: int = 5
) -> tuple[list[UserStat], int]:
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    total_pages = max(1, math.ceil(total_users / per_page))
    page = max(1, min(page, total_pages))
    users = (
        await session.execute(
            select(User).order_by(User.created_at, User.telegram_id)
            .limit(per_page).offset((page - 1) * per_page)
        )
    ).scalars().all()

    rows: list[UserStat] = []
    for u in users:
        confirmed = Booking.status == BookingStatus.CONFIRMED
        agg = (
            await session.execute(
                select(
                    func.count(Booking.id),
                    func.coalesce(func.sum(Booking.people_count), 0),
                    func.max(Booking.date),
                ).where(Booking.user_id == u.telegram_id, confirmed)
            )
        ).first()
        count, people, last = agg[0], int(agg[1]), agg[2]
        fav = await _favorite_branch(session, u.telegram_id)
        rows.append(
            UserStat(
                name=u.full_name,
                phone=u.phone,
                bookings=count,
                people=people,
                first_seen=u.created_at.date() if u.created_at else None,
                last_booking=last,
                favorite_branch=fav,
            )
        )
    return rows, total_pages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_stats.py -v`
Expected: PASS (2 passed). If `first_seen` is `None` in tests (server_default not populated on in-memory rows until refresh), adjust the test seed to `await s.refresh(user)` or accept `None`; the production path always has `created_at`.

- [ ] **Step 5: Commit**

```bash
git add bot/services/stats.py tests/test_stats.py
git commit -m "feat: add stats service for overview and per-user analytics"
```

---

### Task 6: FSM states & keyboards

**Files:**
- Create: `bot/states.py`
- Create: `bot/keyboards/__init__.py` (empty)
- Create: `bot/keyboards/common.py`
- Create: `bot/keyboards/booking.py`
- Create: `bot/keyboards/admin.py`

**Interfaces:**
- Consumes: `t` from Task 3, `LANGUAGES`.
- Produces FSM `StatesGroup`s: `Registration(full_name, phone)`, `Booking(branch, day, time, people, confirm)`, `AddBranch(name, address, open_hour, close_hour)`.
- Produces keyboard builders returning aiogram markup:
  - `language_kb()`, `main_menu_kb(lang)`, `phone_kb(lang)`, `back_kb(lang, cb)`.
  - `branches_kb(branches, lang)`, `days_kb(days, lang)`, `times_kb(hours, lang)`, `confirm_kb(lang)`.
  - `my_bookings_kb(bookings, lang)`.
  - `admin_branches_kb(branches, lang)`.
- Callback-data prefixes (documented, used by handlers): `lang:<code>`, `menu:<action>`, `branch:<id>`, `day:<iso>`, `time:<hour>`, `confirm:yes|no`, `cancelbk:<booking_id>`, `abranch:add`, `abranch:edit:<id>`, `abranch:toggle:<id>`.

- [ ] **Step 1: Create `bot/states.py`**

```python
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    phone = State()


class Booking(StatesGroup):
    branch = State()
    day = State()
    time = State()
    people = State()
    confirm = State()


class AddBranch(StatesGroup):
    name = State()
    address = State()
    open_hour = State()
    close_hour = State()
```

- [ ] **Step 2: Create `bot/keyboards/common.py`**

```python
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import LANGUAGES, t


def language_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, label in LANGUAGES.items():
        b.button(text=label, callback_data=f"lang:{code}")
    b.adjust(1)
    return b.as_markup()


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_book", lang), callback_data="menu:book")
    b.button(text=t("btn_my_bookings", lang), callback_data="menu:mybookings")
    b.button(text=t("btn_language", lang), callback_data="menu:language")
    b.adjust(1)
    return b.as_markup()


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("share_phone_button", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
```

- [ ] **Step 3: Create `bot/keyboards/booking.py`**

```python
from datetime import date

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def branches_kb(branches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=br.name, callback_data=f"branch:{br.id}")
    b.adjust(1)
    return b.as_markup()


def days_kb(days: list[date], lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = days[0]
    for d in days:
        if d == today:
            label = t("today", lang)
        elif (d - today).days == 1:
            label = t("tomorrow", lang)
        else:
            label = d.strftime("%d.%m")
        b.button(text=label, callback_data=f"day:{d.isoformat()}")
    b.adjust(3)
    return b.as_markup()


def times_kb(hours: list[int], lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for h in hours:
        b.button(text=f"{h:02d}:00", callback_data=f"time:{h}")
    b.adjust(4)
    return b.as_markup()


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_confirm", lang), callback_data="confirm:yes")
    b.button(text=t("btn_cancel", lang), callback_data="confirm:no")
    b.adjust(2)
    return b.as_markup()


def my_bookings_kb(bookings, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.button(
            text=t("btn_cancel_booking", lang, date=bk.date.strftime("%d.%m"), hour=bk.start_hour),
            callback_data=f"cancelbk:{bk.id}",
        )
    b.adjust(1)
    return b.as_markup()
```

- [ ] **Step 4: Create `bot/keyboards/admin.py`**

```python
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def admin_branches_kb(branches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for br in branches:
        b.button(text=t("btn_edit", lang, name=br.name), callback_data=f"abranch:edit:{br.id}")
        b.button(text=t("btn_toggle_active", lang), callback_data=f"abranch:toggle:{br.id}")
    b.button(text=t("btn_add_branch", lang), callback_data="abranch:add")
    b.adjust(2)
    return b.as_markup()
```

- [ ] **Step 5: Sanity import check**

Run: `python -c "import bot.states, bot.keyboards.common, bot.keyboards.booking, bot.keyboards.admin; print('ok')"`
Expected: prints `ok`

- [ ] **Step 6: Commit**

```bash
git add bot/states.py bot/keyboards/
git commit -m "feat: add FSM states and inline/reply keyboards"
```

---

### Task 7: User-loading middleware

**Files:**
- Create: `bot/middlewares/__init__.py` (empty)
- Create: `bot/middlewares/user.py`

**Interfaces:**
- Consumes: `User` model, `make_session_factory`.
- Produces: `UserMiddleware(session_factory)` — an aiogram `BaseMiddleware`. On every update it opens a session, loads the `User` by `event.from_user.id`, and injects `data["session_factory"]`, `data["user"]` (the `User` or `None`), and `data["lang"]` (`user.language` or default `"ru"`). Handlers open their own sessions from `session_factory` for writes.

- [ ] **Step 1: Create `bot/middlewares/user.py`**

```python
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.models import User


class UserMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["session_factory"] = self.session_factory
        tg_user = data.get("event_from_user")
        user = None
        if tg_user is not None:
            async with self.session_factory() as session:
                user = await session.get(User, tg_user.id)
        data["user"] = user
        data["lang"] = user.language if user else "ru"
        return await handler(event, data)
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.middlewares.user import UserMiddleware; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/middlewares/
git commit -m "feat: add middleware to load user + language into handler context"
```

---

### Task 8: Admin notification service

**Files:**
- Create: `bot/services/notify.py`

**Interfaces:**
- Consumes: `Settings.admin_ids`, `t`, `Booking` (with `branch` + `user` loaded).
- Produces:
  - `async notify_new_booking(bot, admin_ids, booking, user)` — DMs each admin the `admin_new_booking` string (admin messages always in `ru`; admins are staff).
  - `async notify_cancellation(bot, admin_ids, booking, user)` — DMs each admin the `admin_cancelled` string.
  - Both swallow per-admin send errors (e.g. admin never opened the bot) and continue.

- [ ] **Step 1: Create `bot/services/notify.py`**

```python
import logging

from aiogram import Bot

from bot.locales import t

logger = logging.getLogger(__name__)

ADMIN_LANG = "ru"


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001 - best-effort notification
        logger.warning("Failed to notify admin %s: %s", chat_id, exc)


async def notify_new_booking(bot: Bot, admin_ids, booking, user) -> None:
    text = t(
        "admin_new_booking", ADMIN_LANG,
        branch=booking.branch.name, date=booking.date.isoformat(),
        hour=booking.start_hour, people=booking.people_count,
        name=user.full_name, phone=user.phone,
    )
    for admin_id in admin_ids:
        await _safe_send(bot, admin_id, text)


async def notify_cancellation(bot: Bot, admin_ids, booking, user) -> None:
    text = t(
        "admin_cancelled", ADMIN_LANG,
        branch=booking.branch.name, date=booking.date.isoformat(),
        hour=booking.start_hour, name=user.full_name, phone=user.phone,
    )
    for admin_id in admin_ids:
        await _safe_send(bot, admin_id, text)
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.services.notify import notify_new_booking, notify_cancellation; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/services/notify.py
git commit -m "feat: add best-effort admin notification service"
```

---

### Task 9: Registration & main-menu handler

**Files:**
- Create: `bot/handlers/__init__.py` (empty)
- Create: `bot/handlers/start.py`

**Interfaces:**
- Consumes: `Registration` states, `language_kb`, `main_menu_kb`, `phone_kb`, `t`, `User`, `session_factory` (from middleware data).
- Produces: `router` (aiogram `Router`). Registers `/start`, language callbacks, and the registration FSM. On completion the user row exists and the main menu is shown. Exposes `async def show_main_menu(message_or_cb, lang)` helper reused by other routers via import.

- [ ] **Step 1: Create `bot/handlers/start.py`**

```python
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.models import User
from bot.keyboards.common import language_kb, main_menu_kb, phone_kb
from bot.locales import t
from bot.states import Registration

router = Router()


async def show_main_menu_message(message: Message, lang: str) -> None:
    await message.answer(t("main_menu_title", lang), reply_markup=main_menu_kb(lang))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User | None):
    await state.clear()
    if user is not None:
        await show_main_menu_message(message, user.language)
        return
    await message.answer(t("choose_language", "ru"), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def pick_language(cb: CallbackQuery, state: FSMContext, user: User | None,
                        session_factory):
    lang = cb.data.split(":", 1)[1]
    if user is not None:
        # Language change from menu: persist immediately.
        async with session_factory() as session:
            db_user = await session.get(User, user.telegram_id)
            db_user.language = lang
            await session.commit()
        await cb.message.answer(t("main_menu_title", lang), reply_markup=main_menu_kb(lang))
        await cb.answer()
        return
    await state.update_data(language=lang)
    await state.set_state(Registration.full_name)
    await cb.message.answer(t("ask_full_name", lang))
    await cb.answer()


@router.message(Registration.full_name, F.text)
async def reg_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.phone)
    await message.answer(t("ask_phone", lang), reply_markup=phone_kb(lang))


@router.message(Registration.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext, session_factory):
    data = await state.get_data()
    lang = data["language"]
    async with session_factory() as session:
        session.add(User(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=message.contact.phone_number,
            language=lang,
        ))
        await session.commit()
    await state.clear()
    from aiogram.types import ReplyKeyboardRemove
    await message.answer(t("registered", lang, name=data["full_name"]),
                         reply_markup=ReplyKeyboardRemove())
    await show_main_menu_message(message, lang)


@router.message(Registration.phone)
async def reg_phone_wrong(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(t("phone_use_button", data["language"]),
                         reply_markup=phone_kb(data["language"]))


@router.callback_query(F.data == "menu:language")
async def menu_language(cb: CallbackQuery):
    await cb.message.answer(t("choose_language", "ru"), reply_markup=language_kb())
    await cb.answer()
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.handlers.start import router; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/__init__.py bot/handlers/start.py
git commit -m "feat: add registration and main-menu handler"
```

---

### Task 10: Booking wizard handler

**Files:**
- Create: `bot/handlers/booking.py`

**Interfaces:**
- Consumes: `Booking` states, booking keyboards, `slots` service, `notify` service, `get_settings`, `show_main_menu_message`.
- Produces: `router`. Implements the branch → day → time → people → confirm flow, creating the booking and notifying admins.

- [ ] **Step 1: Create `bot/handlers/booking.py`**

```python
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import User
from bot.keyboards.booking import branches_kb, confirm_kb, days_kb, times_kb
from bot.locales import t
from bot.services import notify, slots
from bot.states import Booking

router = Router()


def _now() -> datetime:
    return datetime.now()


@router.callback_query(F.data == "menu:book")
async def start_booking(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    async with session_factory() as session:
        branches = await slots.list_active_branches(session)
    if not branches:
        await cb.message.answer(t("no_branches", lang))
        await cb.answer()
        return
    await state.set_state(Booking.branch)
    await cb.message.answer(t("choose_branch", lang), reply_markup=branches_kb(branches, lang))
    await cb.answer()


@router.callback_query(Booking.branch, F.data.startswith("branch:"))
async def pick_branch(cb: CallbackQuery, state: FSMContext, lang: str):
    branch_id = int(cb.data.split(":")[1])
    await state.update_data(branch_id=branch_id)
    await state.set_state(Booking.day)
    days = slots.next_days(_now().date())
    await cb.message.answer(t("choose_day", lang), reply_markup=days_kb(days, lang))
    await cb.answer()


@router.callback_query(Booking.day, F.data.startswith("day:"))
async def pick_day(cb: CallbackQuery, state: FSMContext, lang: str, session_factory):
    day = date.fromisoformat(cb.data.split(":", 1)[1])
    data = await state.get_data()
    async with session_factory() as session:
        branch = await slots.get_branch(session, data["branch_id"])
        hours = await slots.free_hours(session, branch, day, _now())
    if not hours:
        await cb.message.answer(t("no_slots", lang))
        await cb.answer()
        return
    await state.update_data(day=day.isoformat())
    await state.set_state(Booking.time)
    await cb.message.answer(t("choose_time", lang), reply_markup=times_kb(hours, lang))
    await cb.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(cb: CallbackQuery, state: FSMContext, lang: str):
    hour = int(cb.data.split(":")[1])
    await state.update_data(hour=hour)
    await state.set_state(Booking.people)
    await cb.message.answer(t("ask_people", lang))
    await cb.answer()


@router.message(Booking.people, F.text)
async def enter_people(message: Message, state: FSMContext, lang: str, session_factory):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer(t("people_invalid", lang))
        return
    data = await state.update_data(people=int(text))
    async with session_factory() as session:
        branch = await slots.get_branch(session, data["branch_id"])
    await state.set_state(Booking.confirm)
    await message.answer(
        t("confirm_title", lang, branch=branch.name, date=data["day"],
          hour=data["hour"], people=data["people"]),
        reply_markup=confirm_kb(lang),
    )


@router.callback_query(Booking.confirm, F.data == "confirm:no")
async def confirm_no(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.message.answer(t("cancelled_flow", lang))
    await cb.answer()


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def confirm_yes(cb: CallbackQuery, state: FSMContext, lang: str, bot: Bot, session_factory):
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    async with session_factory() as session:
        booking = await slots.create_booking(
            session, cb.from_user.id, data["branch_id"], day, data["hour"], data["people"]
        )
        if booking is None:
            # Slot taken between listing and confirm -> re-list times.
            branch = await slots.get_branch(session, data["branch_id"])
            hours = await slots.free_hours(session, branch, day, _now())
            await state.set_state(Booking.time)
            await cb.message.answer(t("slot_taken", lang), reply_markup=times_kb(hours, lang))
            await cb.answer()
            return
        # Reload with relationships for notification + display.
        branch = await slots.get_branch(session, data["branch_id"])
        user = await session.get(User, cb.from_user.id)
        booking.branch = branch
    await state.clear()
    await cb.message.answer(
        t("booking_confirmed", lang, branch=branch.name, date=data["day"], hour=data["hour"])
    )
    await notify.notify_new_booking(bot, get_settings().admin_ids, booking, user)
    await cb.answer()
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.handlers.booking import router; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/booking.py
git commit -m "feat: add booking wizard handler with double-book recovery"
```

---

### Task 11: My-bookings handler

**Files:**
- Create: `bot/handlers/mybookings.py`

**Interfaces:**
- Consumes: `slots.upcoming_bookings`, `slots.cancel_booking`, `my_bookings_kb`, `notify.notify_cancellation`, `get_settings`.
- Produces: `router`. Handles `/mybookings`, `menu:mybookings` callback, and `cancelbk:<id>` cancellation.

- [ ] **Step 1: Create `bot/handlers/mybookings.py`**

```python
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.db.models import User
from bot.keyboards.booking import my_bookings_kb
from bot.locales import t
from bot.services import notify, slots

router = Router()


async def _render_bookings(target, user_id: int, lang: str, session_factory) -> None:
    async with session_factory() as session:
        bookings = await slots.upcoming_bookings(session, user_id, datetime.now())
    if not bookings:
        await target.answer(t("my_bookings_empty", lang))
        return
    lines = [
        t("booking_line", lang, branch=b.branch.name, date=b.date.isoformat(),
          hour=b.start_hour, people=b.people_count)
        for b in bookings
    ]
    text = t("my_bookings_title", lang) + "\n\n" + "\n".join(lines)
    await target.answer(text, reply_markup=my_bookings_kb(bookings, lang))


@router.message(Command("mybookings"))
async def cmd_my_bookings(message: Message, lang: str, session_factory):
    await _render_bookings(message, message.from_user.id, lang, session_factory)


@router.callback_query(F.data == "menu:mybookings")
async def menu_my_bookings(cb: CallbackQuery, lang: str, session_factory):
    await _render_bookings(cb.message, cb.from_user.id, lang, session_factory)
    await cb.answer()


@router.callback_query(F.data.startswith("cancelbk:"))
async def cancel_booking(cb: CallbackQuery, lang: str, bot: Bot, session_factory):
    booking_id = int(cb.data.split(":")[1])
    async with session_factory() as session:
        booking = await slots.cancel_booking(session, booking_id, cb.from_user.id)
        user = await session.get(User, cb.from_user.id)
    if booking is None:
        await cb.answer()
        return
    await cb.message.answer(t("booking_cancelled_user", lang))
    await notify.notify_cancellation(bot, get_settings().admin_ids, booking, user)
    await cb.answer()
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.handlers.mybookings import router; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/mybookings.py
git commit -m "feat: add my-bookings listing and cancellation handler"
```

---

### Task 12: Admin stats handler

**Files:**
- Create: `bot/handlers/admin.py`

**Interfaces:**
- Consumes: `stats` service, `get_settings`, `t`.
- Produces: `router`. Handles `/stats` and `/users` (with `users:page:<n>` pagination). Guarded so only `ADMIN_IDS` get responses; others get `not_authorized`. Admin UI in `ru`.

- [ ] **Step 1: Create `bot/handlers/admin.py`**

```python
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.locales import t
from bot.services import stats

router = Router()
LANG = "ru"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    async with session_factory() as session:
        ov = await stats.overview(session, date.today())
    by_branch = "\n".join(
        t("stats_branch_line", LANG, name=n, count=c) for n, c in ov["by_branch"]
    ) or "—"
    await message.answer(t(
        "stats_overview", LANG, users=ov["users"], bookings=ov["bookings"],
        today=ov["today"], by_branch=by_branch,
    ))


def _users_page_kb(page: int, pages: int):
    b = InlineKeyboardBuilder()
    if page > 1:
        b.button(text="⬅️", callback_data=f"users:page:{page - 1}")
    if page < pages:
        b.button(text="➡️", callback_data=f"users:page:{page + 1}")
    return b.as_markup()


async def _render_users(target, page: int, session_factory):
    async with session_factory() as session:
        rows, pages = await stats.user_stats_page(session, page)
    header = t("users_header", LANG, page=page, pages=pages)
    cards = "\n\n".join(
        t("user_card", LANG, name=r.name, phone=r.phone, bookings=r.bookings,
          people=r.people, first=r.first_seen, last=r.last_booking or "—",
          fav=r.favorite_branch or "—")
        for r in rows
    ) or "—"
    await target.answer(header + "\n\n" + cards, reply_markup=_users_page_kb(page, pages))


@router.message(Command("users"))
async def cmd_users(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    await _render_users(message, 1, session_factory)


@router.callback_query(F.data.startswith("users:page:"))
async def users_page(cb: CallbackQuery, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    page = int(cb.data.split(":")[2])
    await _render_users(cb.message, page, session_factory)
    await cb.answer()
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.handlers.admin import router; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/admin.py
git commit -m "feat: add admin /stats and /users handlers"
```

---

### Task 13: Admin branch-management handler

**Files:**
- Create: `bot/handlers/admin_branches.py`

**Interfaces:**
- Consumes: `AddBranch` states, `admin_branches_kb`, `Branch` model, `get_settings`.
- Produces: `router`. Handles `/branches`, add-branch FSM, toggle-active, and edit (edit re-runs the add FSM, replacing fields on an existing branch id stored in state).

- [ ] **Step 1: Create `bot/handlers/admin_branches.py`**

```python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import Branch
from bot.keyboards.admin import admin_branches_kb
from bot.locales import t
from bot.states import AddBranch

router = Router()
LANG = "ru"


def _is_admin(user_id: int) -> bool:
    return get_settings().is_admin(user_id)


async def _render_branches(target, session_factory):
    async with session_factory() as session:
        branches = list((await session.execute(select(Branch).order_by(Branch.name))).scalars().all())
    lines = [
        t("branch_admin_line", LANG,
          status="🟢" if b.is_active else "🔴", name=b.name,
          open=b.open_hour, close=b.close_hour, address=b.address)
        for b in branches
    ] or ["—"]
    await target.answer(
        t("branches_title", LANG) + "\n" + "\n".join(lines),
        reply_markup=admin_branches_kb(branches, LANG),
    )


@router.message(Command("branches"))
async def cmd_branches(message: Message, session_factory):
    if not _is_admin(message.from_user.id):
        await message.answer(t("not_authorized", LANG))
        return
    await _render_branches(message, session_factory)


@router.callback_query(F.data == "abranch:add")
async def add_branch(cb: CallbackQuery, state: FSMContext):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=None)
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", LANG))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:edit:"))
async def edit_branch(cb: CallbackQuery, state: FSMContext):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    await state.update_data(edit_id=int(cb.data.split(":")[2]))
    await state.set_state(AddBranch.name)
    await cb.message.answer(t("ask_branch_name", LANG))
    await cb.answer()


@router.callback_query(F.data.startswith("abranch:toggle:"))
async def toggle_branch(cb: CallbackQuery, session_factory):
    if not _is_admin(cb.from_user.id):
        await cb.answer()
        return
    branch_id = int(cb.data.split(":")[2])
    async with session_factory() as session:
        branch = await session.get(Branch, branch_id)
        if branch:
            branch.is_active = not branch.is_active
            await session.commit()
    await cb.answer(t("branch_toggled", LANG))
    await _render_branches(cb.message, session_factory)


@router.message(AddBranch.name, F.text)
async def branch_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddBranch.address)
    await message.answer(t("ask_branch_address", LANG))


@router.message(AddBranch.address, F.text)
async def branch_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(AddBranch.open_hour)
    await message.answer(t("ask_open_hour", LANG))


@router.message(AddBranch.open_hour, F.text)
async def branch_open(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 23):
        await message.answer(t("hour_invalid", LANG))
        return
    await state.update_data(open_hour=int(text))
    await state.set_state(AddBranch.close_hour)
    await message.answer(t("ask_close_hour", LANG))


@router.message(AddBranch.close_hour, F.text)
async def branch_close(message: Message, state: FSMContext, session_factory):
    text = message.text.strip()
    data = await state.get_data()
    if not text.isdigit() or not (1 <= int(text) <= 24) or int(text) <= data["open_hour"]:
        await message.answer(t("hour_invalid", LANG))
        return
    close_hour = int(text)
    async with session_factory() as session:
        if data.get("edit_id"):
            branch = await session.get(Branch, data["edit_id"])
            branch.name = data["name"]
            branch.address = data["address"]
            branch.open_hour = data["open_hour"]
            branch.close_hour = close_hour
        else:
            session.add(Branch(
                name=data["name"], address=data["address"],
                open_hour=data["open_hour"], close_hour=close_hour, is_active=True,
            ))
        await session.commit()
    await state.clear()
    await message.answer(t("branch_saved", LANG))
    await _render_branches(message, session_factory)
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "from bot.handlers.admin_branches import router; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/admin_branches.py
git commit -m "feat: add admin branch management handler"
```

---

### Task 14: Entrypoint wiring, README, and end-to-end smoke test

**Files:**
- Create: `bot/main.py`
- Create: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `async def main()` that builds the bot, DB, middleware, includes all routers, and starts polling. `python -m bot.main` runs the bot.

- [ ] **Step 1: Create `bot/main.py`**

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.db.base import init_db, make_engine, make_session_factory
from bot.handlers import admin, admin_branches, booking, mybookings, start
from bot.middlewares.user import UserMiddleware


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    engine = make_engine(settings.db_path)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    bot = Bot(settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    middleware = UserMiddleware(session_factory)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(mybookings.router)
    dp.include_router(admin.router)
    dp.include_router(admin_branches.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Create `README.md`**

````markdown
# Mini Carting Booking Bot

Telegram bot for a Tashkent go-kart service: customers register and book hourly
slots; admins get notified and view analytics + manage branches.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit BOT_TOKEN and ADMIN_IDS
```

Get `BOT_TOKEN` from [@BotFather](https://t.me/BotFather). `ADMIN_IDS` is a
comma-separated list of Telegram user ids (get yours from @userinfobot).

## Run

```bash
python -m bot.main
```

## Test

```bash
python -m pytest -v
```

## Usage

- **Users:** `/start` → pick language → name → share phone → main menu →
  Book a slot (branch → day → time → people → confirm). `/mybookings` to view
  or cancel.
- **Admins:** get a DM on each new booking/cancellation. `/stats` for an
  overview, `/users` for per-customer analytics, `/branches` to add/edit or
  activate/deactivate branches.

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, booking, my-bookings, admin).
- `bot/services/` — tested business logic (slots, stats, notifications).
- `bot/db/` — SQLAlchemy async models + engine; slots are computed, not stored.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
````

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS (all tests from Tasks 1–5 green)

- [ ] **Step 4: Import-wire smoke check**

Run: `python -c "import bot.main; print('wired')"`
Expected: prints `wired` (no import/wiring errors)

- [ ] **Step 5: Manual end-to-end smoke test (requires a real bot token)**

1. Put a real `BOT_TOKEN` and your Telegram id in `.env`.
2. `python -m bot.main`
3. In Telegram: `/start` → choose language → enter name → tap **Share number**.
4. Tap **Book** → pick a branch (first add one via `/branches` as admin) → pick day → time → enter people → **Confirm**.
5. Verify you (as admin) receive the new-booking DM.
6. `/mybookings` → **Cancel** → verify admin cancellation DM and that the slot reappears when rebooking.
7. `/stats` and `/users` show the booking.

Expected: all steps succeed. Note anything that fails for follow-up.

- [ ] **Step 6: Commit**

```bash
git add bot/main.py README.md
git commit -m "feat: wire dispatcher entrypoint and add README"
```

---

## Self-Review Notes

- **Spec coverage:** registration+language (T9), phone share-only (T9), booking flow (T10), computed slots+double-book guard (T2/T4/T10), my-bookings+cancel (T11), admin notifications (T8/T10/T11), stats overview+per-user (T5/T12), branch management (T13), ru/uz i18n (T3), SQLite/SQLAlchemy async (T2), project structure (all). All spec sections map to a task.
- **Type consistency:** service signatures declared in Interfaces match call sites in handlers (`create_booking(session, user_id, branch_id, day, hour, people)`, `cancel_booking(session, booking_id, user_id)`, `free_hours(session, branch, day, now)`, `overview(session, today)`, `user_stats_page(session, page)`).
- **Callback-data prefixes** are consistent across keyboards (T6) and handlers (T9–T13): `lang:`, `menu:`, `branch:`, `day:`, `time:`, `confirm:`, `cancelbk:`, `abranch:`, `users:page:`.
- **Note for implementer:** In Task 4 use the simplified `upcoming_bookings` loop body shown in the second code block.
