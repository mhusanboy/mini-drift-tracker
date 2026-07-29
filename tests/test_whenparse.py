from datetime import date

import pytest

from bot.services.whenparse import parse_when

TODAY = date(2026, 7, 16)      # a Thursday
TOMORROW = date(2026, 7, 17)


@pytest.mark.parametrize("text,expected_day,expected_min", [
    # day words, both languages
    ("ertaga soat 18:00", TOMORROW, 18 * 60),
    ("bugun 19:30", TODAY, 19 * 60 + 30),
    ("завтра в 18:00", TOMORROW, 18 * 60),
    ("сегодня 20:00", TODAY, 20 * 60),
    # month names
    ("25-iyul, 19:30", date(2026, 7, 25), 19 * 60 + 30),
    ("25 июля 19:30", date(2026, 7, 25), 19 * 60 + 30),
    ("3-avgust 11:00", date(2026, 8, 3), 11 * 60),
    # numeric dates
    ("25.07 18:00", date(2026, 7, 25), 18 * 60),
    ("25/07 18:00", date(2026, 7, 25), 18 * 60),
    ("25.07.2026 18:00", date(2026, 7, 25), 18 * 60),
    ("25.07 18", date(2026, 7, 25), 18 * 60),
    # time only -> today
    ("18:00", TODAY, 18 * 60),
    ("18", TODAY, 18 * 60),
    ("18.30", TODAY, 18 * 60 + 30),
])
def test_understands(text, expected_day, expected_min):
    assert parse_when(text, TODAY) == (expected_day, expected_min)


@pytest.mark.parametrize("text", [
    "",
    "shanba kuni kechqurun",   # a day with no time
    "как-нибудь вечером",
    "25.07",                   # a date with no time is not bookable
    "1800",                    # not a time anyone writes
])
def test_gives_up_rather_than_guessing(text):
    assert parse_when(text, TODAY) == (None, None)


def test_a_date_already_past_rolls_to_next_year():
    # January, asked for in July, means next January.
    assert parse_when("25.01 18:00", TODAY) == (date(2027, 1, 25), 18 * 60)


def test_explicit_year_is_respected():
    assert parse_when("25.07.2027 18:00", TODAY) == (date(2027, 7, 25), 18 * 60)


def test_dotted_time_is_not_mistaken_for_a_date():
    # 18.30 has no valid month, so it can only be a time.
    assert parse_when("18.30", TODAY) == (TODAY, 18 * 60 + 30)


def test_a_real_date_wins_when_a_time_is_also_present():
    # 12.05 is ambiguous alone; the explicit 19:00 settles it as a date.
    assert parse_when("12.05 19:00", TODAY) == (date(2027, 5, 12), 19 * 60)


def test_impossible_clock_values_are_rejected():
    assert parse_when("99:99", TODAY) == (None, None)


def test_declined_month_names_still_match():
    assert parse_when("25 июля 18:00", TODAY)[0] == date(2026, 7, 25)
    assert parse_when("5 марта 18:00", TODAY)[0] == date(2027, 3, 5)
