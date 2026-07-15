import logging

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def make_engine(db_path: str) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _default_literal(column) -> str | None:
    """Render a column's Python-side scalar default as a SQL literal (for
    ALTER TABLE ADD COLUMN ... DEFAULT). Returns None if there is none."""
    default = column.default
    if default is None or not getattr(default, "is_scalar", False):
        return None
    value = default.arg
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _migrate(sync_conn) -> None:
    """Additive, in-place migration: create any missing tables, then ADD COLUMN
    for any model column not present in an existing table. Never drops or renames
    (so no data is lost). New columns should carry a default so existing rows are
    backfilled and NOT NULL constraints can be honoured."""
    Base.metadata.create_all(sync_conn)  # missing tables (e.g. day_offs)

    inspector = inspect(sync_conn)
    for table in Base.metadata.sorted_tables:
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            coltype = column.type.compile(dialect=sync_conn.dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {coltype}'
            default = _default_literal(column)
            if default is not None:
                ddl += f" DEFAULT {default}"
                if not column.nullable:
                    ddl += " NOT NULL"
            # A NOT NULL column with no default can't be added to a populated
            # table in SQLite; add it nullable so at least the column exists.
            sync_conn.exec_driver_sql(ddl)
            logger.info("Migrated: added column %s.%s", table.name, column.name)


async def init_db(engine: AsyncEngine) -> None:
    # Import models so they register on Base.metadata before migrating.
    from bot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(_migrate)
