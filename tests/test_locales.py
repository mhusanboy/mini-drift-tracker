from bot.locales import _STRINGS, LANGUAGES, t


def test_returns_localized_string():
    assert t("choose_language", "ru") != t("choose_language", "uz")


def test_formatting_kwargs():
    msg = t("booking_dm_template", "uz", name="Anvar", when="ertaga 18:00",
            phone="+998", people=3)
    assert "Anvar" in msg and "ertaga 18:00" in msg and "+998" in msg and "3" in msg


def test_unknown_lang_falls_back_to_ru():
    assert t("main_menu_title", "de") == t("main_menu_title", "ru")


def test_missing_key_returns_key():
    assert t("__nope__", "ru") == "__nope__"


def test_languages_map():
    assert set(LANGUAGES) == {"ru", "uz"}


def test_both_locales_define_the_same_keys():
    assert set(_STRINGS["ru"]) == set(_STRINGS["uz"])
