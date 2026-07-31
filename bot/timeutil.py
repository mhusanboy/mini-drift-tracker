"""Parsing and formatting of clock times, and the bot's local clock.

The service runs in Asia/Tashkent (UTC+5, no DST). The droplet's system clock is
UTC, so every read of "now"/"today" goes through the helpers below rather than
``datetime.now()`` directly. They return **naive** datetimes carrying local
wall-clock time — the rest of the code does naive arithmetic (slot minutes, day
boundaries), so mixing in a tz-aware value would raise.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

DAY_MINUTES = 24 * 60

TZ = ZoneInfo("Asia/Tashkent")


def now_local() -> datetime:
    """Current Tashkent wall-clock time, as a naive datetime."""
    return datetime.now(TZ).replace(tzinfo=None)


def today_local() -> date:
    """Today's date in Tashkent."""
    return now_local().date()


def parse_time(text: str) -> int | None:
    """Parse ``11`` / ``11:00`` / ``11.30`` into minutes since midnight.

    Returns the total minutes (0..1440, where 1440 == 24:00 midnight) or
    ``None`` if the text is not a valid time.
    """
    text = text.strip().replace(".", ":")
    if not text:
        return None
    parts = text.split(":")
    if len(parts) > 2 or not all(p.isdigit() for p in parts):
        return None
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) == 2 else 0
    if minute > 59:
        return None
    total = hour * 60 + minute
    if total > DAY_MINUTES or (total == DAY_MINUTES and minute != 0):
        return None
    return total


def format_time(hour: int, minute: int = 0) -> str:
    return f"{hour:02d}:{minute:02d}"


def fmt_minutes(minutes: int) -> str:
    """Format minutes-since-midnight as HH:MM (e.g. 690 -> '11:30')."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
