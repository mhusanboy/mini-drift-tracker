"""Parsing and formatting of clock times entered by admins.

Opening/closing times accept ``11``, ``11:00`` and ``11:30``. Values are stored
as an (hour, minute) pair on the branch; bookable slots remain on the hour, so a
half-hour opening simply pushes the first slot to the next full hour.
"""
DAY_MINUTES = 24 * 60


def parse_time(text: str) -> int | None:
    """Parse ``11`` / ``11:00`` / ``11:30`` into minutes since midnight.

    Returns the total minutes (0..1440, where 1440 == 24:00 midnight) or
    ``None`` if the text is not a valid time.
    """
    text = text.strip()
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
