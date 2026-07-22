"""Understanding the day and time a customer typed.

Customers write freely ("ertaga soat 18:00", "25-iyul 19:30"), but tracking free
and busy times needs a real date. This is best-effort: when the text cannot be
understood the request is still created, flagged as time-unknown, and the admin
sets it by hand.
"""
import re
from datetime import date, timedelta

TODAY_WORDS = ("bugun", "сегодня", "today")
TOMORROW_WORDS = ("ertaga", "эртага", "завтра", "tomorrow")

# Matched by prefix so declensions still hit ("iyulda", "июля", "марта").
_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11,
    "dekabr": 12,
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "май": 5, "мая": 5,
    "июн": 6, "июл": 7, "август": 8, "сентябр": 9, "октябр": 10,
    "ноябр": 11, "декабр": 12,
}
# Longest first, so "март" wins over a shorter prefix of the same word.
_MONTH_KEYS = sorted(_MONTHS, key=len, reverse=True)

_COLON_TIME = re.compile(r"(\d{1,2})\s*:\s*(\d{2})")
_DOT_TIME = re.compile(r"(\d{1,2})\s*\.\s*(\d{2})")
_NUMERIC_DATE = re.compile(r"(\d{1,2})\s*[./-]\s*(\d{1,2})(?:\s*[./-]\s*(\d{2,4}))?")
_DAY_MONTH = re.compile(r"(\d{1,2})\s*-?\s*([^\W\d_]+)")
_BARE_HOUR = re.compile(r"\b(\d{1,2})\b")


def _cut(text: str, match: re.Match) -> str:
    return text[: match.start()] + " " + text[match.end():]


def _month_of(word: str) -> int | None:
    for key in _MONTH_KEYS:
        if word.startswith(key):
            return _MONTHS[key]
    return None


def _time_of(match: re.Match) -> int | None:
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _make_date(day: int, month: int, year: int | None, today: date) -> date | None:
    if year is not None:
        try:
            return date(year + 2000 if year < 100 else year, month, day)
        except ValueError:
            return None
    # No year given: the nearest one that hasn't passed yet.
    for candidate_year in (today.year, today.year + 1):
        try:
            candidate = date(candidate_year, month, day)
        except ValueError:
            continue
        if candidate >= today:
            return candidate
    return None


def parse_when(text: str, today: date) -> tuple[date | None, int | None]:
    """Return (day, minutes-since-midnight), or (None, None) if unintelligible.

    A time with no day at all is read as today — the admin sees the resolved
    date on the request card and can correct it.
    """
    body = f" {text.lower().strip()} "
    day: date | None = None
    start: int | None = None

    # 1. An unambiguous HH:MM wins before any date parsing eats the digits.
    match = _COLON_TIME.search(body)
    if match and (start := _time_of(match)) is not None:
        body = _cut(body, match)

    # 2. "bugun" / "ertaga" / "завтра"
    for words, offset in ((TODAY_WORDS, 0), (TOMORROW_WORDS, 1)):
        for word in words:
            if word in body:
                day = today + timedelta(days=offset)
                body = body.replace(word, " ")
                break
        if day is not None:
            break

    # 3. 25.07 / 25/07 / 25-07-2026
    if day is None:
        for match in _NUMERIC_DATE.finditer(body):
            found = _make_date(
                int(match.group(1)), int(match.group(2)),
                int(match.group(3)) if match.group(3) else None, today,
            )
            if found is not None:
                day, body = found, _cut(body, match)
                break

    # 4. 25-iyul / 25 июля
    if day is None:
        for match in _DAY_MONTH.finditer(body):
            month = _month_of(match.group(2))
            if month is None:
                continue
            found = _make_date(int(match.group(1)), month, None, today)
            if found is not None:
                day, body = found, _cut(body, match)
                break

    # 5. Only now is a bare "18.00" or "18" safe to read as a time.
    if start is None:
        match = _DOT_TIME.search(body)
        if match:
            start = _time_of(match)
    if start is None:
        match = _BARE_HOUR.search(body)
        if match and int(match.group(1)) <= 23:
            start = int(match.group(1)) * 60

    if start is None:
        return None, None
    return (day or today), start
