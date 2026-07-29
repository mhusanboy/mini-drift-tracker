import sqlite3

from sqlalchemy import create_engine

from bot.db import models  # noqa: F401  (register tables on Base.metadata)
from bot.db.base import _migrate


def _make_old_db(path):
    """An older schema: branches without location/minute columns, bookings
    without reminder/attendance/rating columns, and no day_offs table."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, full_name TEXT,
            phone TEXT, language TEXT, created_at TEXT);
        CREATE TABLE branches (id INTEGER PRIMARY KEY, name TEXT, address TEXT,
            open_hour INTEGER, close_hour INTEGER, is_active INTEGER, created_at TEXT);
        CREATE TABLE bookings (id INTEGER PRIMARY KEY, user_id INTEGER, branch_id INTEGER,
            date TEXT, start_minute INTEGER, num_hours INTEGER, people_count INTEGER,
            status TEXT, created_at TEXT);
        INSERT INTO users VALUES (1, 'Anvar', '+998', 'uz', '2026-07-15');
        INSERT INTO branches (id, name, address, open_hour, close_hour, is_active)
            VALUES (1, 'Kart', 'X', 10, 22, 1);
        INSERT INTO bookings (id, user_id, branch_id, date, start_minute, num_hours,
            people_count, status) VALUES (1, 1, 1, '2026-07-20', 600, 1, 3, 'confirmed');
        """
    )
    con.commit()
    con.close()


def test_migrate_adds_columns_and_tables_without_losing_data(tmp_path):
    db = tmp_path / "old.db"
    _make_old_db(str(db))

    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        _migrate(conn)
        _migrate(conn)  # idempotent: running again is a no-op

    con = sqlite3.connect(str(db))
    booking_cols = {r[1] for r in con.execute("PRAGMA table_info(bookings)")}
    assert {"reminded", "attended", "rating", "rating_requested", "branch_name"} <= booking_cols
    branch_cols = {r[1] for r in con.execute("PRAGMA table_info(branches)")}
    assert {"open_minute", "close_minute", "latitude", "longitude", "location_url"} <= branch_cols
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "day_offs" in tables

    # Existing row is preserved; new columns get their defaults.
    assert con.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
    branch_name, reminded, people = con.execute(
        "SELECT branch_name, reminded, people_count FROM bookings WHERE id=1"
    ).fetchone()
    assert branch_name == "" and reminded == 0 and people == 3
    con.close()
