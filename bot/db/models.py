from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
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
    open_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    close_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    close_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Location: either a shared Telegram point (lat/lng) or a map link (URL).
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="branch")


class DayOff(Base):
    """A single calendar date on which the service is closed (no bookings).
    Presence of a row = that date is a day-off; toggling adds/removes it."""

    __tablename__ = "day_offs"

    date: Mapped[date] = mapped_column(Date, primary_key=True)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)
    # Nullable so a branch can be deleted while its bookings survive as history.
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    # Denormalized branch name kept even after the branch row is deleted.
    branch_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    num_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
