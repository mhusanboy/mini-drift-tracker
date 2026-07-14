import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from bot.db.base import Base, make_session_factory


@pytest_asyncio.fixture
async def session_factory():
    # StaticPool keeps a single shared connection so the :memory: database
    # (and its schema) is visible across every session opened in a test.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    from bot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()
