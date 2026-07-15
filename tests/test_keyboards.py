from bot.keyboards.admin import admin_panel_kb
from bot.keyboards.common import main_menu_kb


def _callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_main_menu_shows_admin_button_only_for_admins():
    assert "adm:panel" in _callbacks(main_menu_kb("ru", is_admin=True))
    assert "adm:panel" not in _callbacks(main_menu_kb("ru", is_admin=False))
    # Default (non-admin) menu keeps the three customer actions.
    assert _callbacks(main_menu_kb("uz")) == ["menu:book", "menu:mybookings", "menu:language"]


def test_admin_panel_kb_actions():
    assert _callbacks(admin_panel_kb("ru")) == [
        "adm:service", "adm:bookings", "adm:dayoffs", "adm:stats", "adm:users", "adm:export",
    ]
