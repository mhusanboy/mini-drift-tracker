import pytest

from bot.config import Settings


def test_admin_ids_parsed_from_csv():
    s = Settings(bot_token="t", admin_ids_raw="111,222", db_path="x.db")
    assert s.admin_ids == [111, 222]
    assert s.is_admin(111) is True
    assert s.is_admin(999) is False


def test_admin_ids_empty():
    s = Settings(bot_token="t", admin_ids_raw="", db_path="x.db")
    assert s.admin_ids == []


@pytest.mark.parametrize("raw,expected", [("111,222", [111, 222]), ("999", [999]), ("", [])])
def test_admin_ids_parsed_from_environment(monkeypatch, raw, expected):
    # Loading from env is the real runtime path: a single "999" or CSV
    # "111,222" must both parse without pydantic-settings JSON-decoding them.
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_IDS", raw)
    monkeypatch.setenv("DB_PATH", "x.db")
    s = Settings(_env_file=None)
    assert s.admin_ids == expected
