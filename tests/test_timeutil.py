import pytest

from bot.timeutil import format_time, parse_time


@pytest.mark.parametrize("text,expected", [
    ("11", 660),
    ("11:00", 660),
    ("11:30", 690),
    ("0", 0),
    ("9:05", 545),
    ("23:59", 1439),
    ("24", 1440),
    ("24:00", 1440),
    (" 11:30 ", 690),
])
def test_parse_valid(text, expected):
    assert parse_time(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "11:60", "11:99", "25:00", "24:30", "11:30:00", "-1", "11:", ":30"])
def test_parse_invalid(text):
    assert parse_time(text) is None


def test_format_time():
    assert format_time(11, 0) == "11:00"
    assert format_time(11, 30) == "11:30"
    assert format_time(9) == "09:00"
