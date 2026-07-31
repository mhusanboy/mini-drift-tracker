from datetime import datetime, timezone

from bot.timeutil import fmt_minutes, now_local, parse_time, today_local


def test_now_local_is_naive_tashkent_time():
    n = now_local()
    assert n.tzinfo is None  # naive, to match the rest of the code
    # Tashkent is UTC+5 year-round (no DST), so local should lead UTC by ~5h.
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    diff_hours = (n - utc).total_seconds() / 3600
    assert 4.5 < diff_hours < 5.5


def test_today_local_matches_now_local():
    assert today_local() == now_local().date()


def test_parse_time_accepts_dot_and_colon():
    assert parse_time("11") == 660
    assert parse_time("11:30") == 690
    assert parse_time("11.30") == 690
    assert parse_time("23:59") == 23 * 60 + 59


def test_parse_time_rejects_nonsense():
    assert parse_time("") is None
    assert parse_time("abc") is None
    assert parse_time("11:70") is None
    assert parse_time("25:00") is None


def test_fmt_minutes():
    assert fmt_minutes(0) == "00:00"
    assert fmt_minutes(690) == "11:30"
