from datetime import date

from bot.keyboards.admin import (
    admin_panel_kb,
    free_times_kb,
    promo_label,
    promos_admin_kb,
    settings_kb,
)
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


def test_free_times_kb_is_a_two_column_grid_with_a_header_per_day():
    days = [{
        "date": date(2026, 7, 20),
        "label": "Bugun",
        "slots": [(660, False), (690, True), (720, False), (750, True)],
    }]
    rows = free_times_kb(days, "uz").inline_keyboard
    # header (label only), then 2-per-row slots, then Back
    assert rows[0][0].callback_data == "free:noop" and "Bugun" in rows[0][0].text
    assert len(rows[1]) == 2
    assert rows[1][0].text == "11:00"           # free: bare time
    assert rows[1][1].text == "11:30 ❌"         # busy: marked
    assert rows[1][0].callback_data == "free:slot:2026-07-20:660"
    assert rows[1][1].callback_data == "free:slot:2026-07-20:690"
    assert rows[-1][0].callback_data == "back:panel"


def test_free_times_kb_wraps_an_odd_final_slot_onto_its_own_row():
    days = [{"date": date(2026, 7, 20), "label": "Bugun",
             "slots": [(660, False), (690, False), (720, False)]}]
    rows = free_times_kb(days, "uz").inline_keyboard
    assert len(rows[1]) == 2 and len(rows[2]) == 1
    assert rows[2][0].callback_data == "free:slot:2026-07-20:720"


def test_booking_link_kb_carries_the_url():
    url = "https://t.me/minidriftuz?text=Salom"
    markup = booking_link_kb(url, "ru")
    assert markup.inline_keyboard[0][0].url == url
    assert _callbacks(markup)[-1] == "back:main"
