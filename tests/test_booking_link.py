from bot.services.booking_link import build, build_message


def test_message_carries_everything_the_admin_needs():
    msg = build_message("uz", "Anvar Anvarov", "+998901234567", "ertaga soat 18:00", 5)
    assert "Anvar Anvarov" in msg
    assert "ertaga soat 18:00" in msg
    assert "+998901234567" in msg
    assert "5" in msg


def test_message_is_localized():
    uz = build_message("uz", "A", "+998", "bugun", 2)
    ru = build_message("ru", "A", "+998", "bugun", 2)
    assert uz != ru


def test_link_points_at_the_username_and_is_encoded():
    _, url = build("uz", "minidriftuz", "Anvar", "+998901234567", "ertaga 18:00", 4)
    assert url.startswith("https://t.me/minidriftuz?text=")
    assert " " not in url
    assert "%0A" in url  # newlines survive as escapes


def test_link_escapes_the_phone_plus():
    # A bare '+' in a query string decodes back to a space, mangling the number.
    _, url = build("uz", "minidriftuz", "Anvar", "+998901234567", "bugun", 1)
    assert "%2B998901234567" in url


def test_link_escapes_reserved_characters_in_free_text():
    _, url = build("uz", "minidriftuz", "A", "+998", "25/07 18:00 & 19:00?", 1)
    for raw in ("/", "&", "?", ":"):
        assert raw not in url.split("?text=", 1)[1]
