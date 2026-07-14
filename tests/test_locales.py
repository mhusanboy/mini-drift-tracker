from bot.locales import LANGUAGES, t


def test_returns_localized_string():
    assert t("choose_language", "ru") != t("choose_language", "uz")


def test_formatting_kwargs():
    msg = t("booking_confirmed", "ru", branch="Main", date="2026-07-20", hour=10, end=12, hours=2)
    assert "Main" in msg and "10" in msg and "12" in msg


def test_unknown_lang_falls_back_to_ru():
    assert t("main_menu_title", "de") == t("main_menu_title", "ru")


def test_missing_key_returns_key():
    assert t("__nope__", "ru") == "__nope__"


def test_languages_map():
    assert set(LANGUAGES) == {"ru", "uz"}
