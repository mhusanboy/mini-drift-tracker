import sqlite3

from sqlalchemy import create_engine

from bot.db import models  # noqa: F401  (register tables on Base.metadata)
from bot.db.base import _migrate


def _make_old_db(path):
    """A pre-rewrite database: no service/promos tables, a users table without
    the language column, and the retired booking tables still present."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, full_name TEXT,
            phone TEXT, created_at TEXT);
        CREATE TABLE branches (id INTEGER PRIMARY KEY, name TEXT, address TEXT);
        CREATE TABLE bookings (id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT);
        INSERT INTO users VALUES (1, 'Anvar', '+998901234567', '2026-07-15');
        INSERT INTO branches VALUES (1, 'Kart', 'Tashkent');
        INSERT INTO bookings VALUES (1, 1, '2026-07-20');
        """
    )
    con.commit()
    con.close()


def _migrated(tmp_path):
    db = tmp_path / "old.db"
    _make_old_db(str(db))
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        _migrate(conn)
        _migrate(conn)  # idempotent: running again is a no-op
    return sqlite3.connect(str(db))


def _tables(con):
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migrate_creates_the_new_tables(tmp_path):
    con = _migrated(tmp_path)
    assert {"service", "promos", "booking_requests"} <= _tables(con)
    con.close()


def test_new_requests_do_not_collide_with_the_old_bookings_table(tmp_path):
    # The old `bookings` table has NOT NULL columns the new model knows nothing
    # about, which is exactly why requests live in their own table.
    con = _migrated(tmp_path)
    con.execute(
        "INSERT INTO booking_requests (user_id, full_name, phone, when_text, "
        "people_count, duration_hours, duration_overridden, status) "
        "VALUES (1, 'Anvar', '+998', 'ertaga 18:00', 4, 1, 0, 'pending')"
    )
    con.commit()
    assert con.execute("SELECT COUNT(*) FROM booking_requests").fetchone()[0] == 1
    con.close()


def test_migrate_adds_missing_columns_with_their_default(tmp_path):
    con = _migrated(tmp_path)
    cols = {r[1] for r in con.execute("PRAGMA table_info(users)")}
    assert "language" in cols
    # The existing row is backfilled rather than lost.
    name, language = con.execute(
        "SELECT full_name, language FROM users WHERE telegram_id=1"
    ).fetchone()
    assert name == "Anvar" and language == "ru"
    con.close()


def test_migrate_leaves_retired_tables_alone(tmp_path):
    # The booking engine is gone from the models, but dropping tables would
    # destroy data; they are simply ignored from here on.
    con = _migrated(tmp_path)
    assert {"branches", "bookings"} <= _tables(con)
    assert con.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1
    con.close()
