from bot.keyboards.admin import admin_panel_kb, promo_label, promos_admin_kb, settings_kb
from bot.keyboards.common import booking_link_kb, main_menu_kb


class _Promo:
    def __init__(self, id, text):
        self.id, self.text = id, text


def _callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_main_menu_customer_actions():
    assert _callbacks(main_menu_kb("uz")) == [
        "menu:location", "menu:prices", "menu:promos", "menu:book", "menu:language",
    ]


def test_main_menu_shows_admin_button_only_for_admins():
    assert "adm:panel" in _callbacks(main_menu_kb("ru", is_admin=True))
    assert "adm:panel" not in _callbacks(main_menu_kb("ru", is_admin=False))


def test_main_menu_has_no_back():
    assert "back:main" not in _callbacks(main_menu_kb("ru", is_admin=True))


def test_admin_panel_kb_actions():
    assert _callbacks(admin_panel_kb("ru")) == [
        "adm:settings", "adm:free", "adm:stats", "adm:history", "adm:users", "back:main",
    ]


def test_settings_kb_actions():
    assert _callbacks(settings_kb("ru")) == [
        "adm:price", "adm:hours", "adm:location", "adm:promos", "adm:username", "back:panel",
    ]


def test_promos_admin_kb_lists_then_offers_add():
    markup = promos_admin_kb([_Promo(3, "A"), _Promo(7, "B")], "ru")
    assert _callbacks(markup) == ["promo:del:3", "promo:del:7", "promo:add", "back:settings"]


def test_promos_admin_kb_with_no_promos():
    assert _callbacks(promos_admin_kb([], "ru")) == ["promo:add", "back:settings"]


def test_promo_label_uses_first_line_and_clips():
    assert promo_label("Chegirma\nBatafsil matn") == "Chegirma"
    long = promo_label("x" * 100)
    assert len(long) <= 28 and long.endswith("…")


def test_booking_link_kb_carries_the_url():
    url = "https://t.me/minidriftuz?text=Salom"
    markup = booking_link_kb(url, "ru")
    assert markup.inline_keyboard[0][0].url == url
    assert _callbacks(markup)[-1] == "back:main"
