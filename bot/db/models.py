from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.timeutil import now_local

PHOTO = "photo"
VIDEO = "video"


class BookingStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False, default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, server_default=func.now())


class Service(Base):
    """Everything the admin configures, as a single row (id == 1)."""

    __tablename__ = "service"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # Free-text price list, shown to customers verbatim.
    price_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Telegram username the "Bron qilish" deep link opens, stored without "@".
    booking_username: Mapped[str | None] = mapped_column(String, nullable=True)
    # Opening hours, needed to work out which times are still free. Null until
    # the admin sets them.
    open_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    close_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    close_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Location: a shared Telegram point (lat/lng, plus a title/address when the
    # admin shares a venue) or a maps link. Either may be unset.
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_url: Mapped[str | None] = mapped_column(String, nullable=True)


class Promo(Base):
    """An "aksiya": description text plus an optional photo or video."""

    __tablename__ = "promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # PHOTO / VIDEO / None. file_id is a Telegram file id, valid for this bot.
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, server_default=func.now())


class Booking(Base):
    """A booking request: raised by a customer, decided by an admin.

    Deliberately not called "bookings" — databases from the retired slot engine
    still carry a table by that name with incompatible NOT NULL columns, and the
    migrator only ever adds.
    """

    __tablename__ = "booking_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)
    # Snapshotted so history still reads correctly if the customer's profile
    # changes later.
    full_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String, nullable=False, default="")
    # Exactly what the customer typed, kept even when it parsed cleanly.
    when_text: Mapped[str] = mapped_column(String, nullable=False, default="")
    # The parsed slot. Null when the text could not be understood and no admin
    # has set it yet — such a request holds no time.
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Set once an admin picks a duration by hand, which stops a later people
    # edit from silently recalculating over it.
    duration_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=BookingStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship()
