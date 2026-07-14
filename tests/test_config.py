from bot.config import Settings


def test_admin_ids_parsed_from_csv():
    s = Settings(bot_token="t", admin_ids="111,222", db_path="x.db")
    assert s.admin_ids == [111, 222]
    assert s.is_admin(111) is True
    assert s.is_admin(999) is False


def test_admin_ids_accepts_list():
    s = Settings(bot_token="t", admin_ids=[5], db_path="x.db")
    assert s.admin_ids == [5]
