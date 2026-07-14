import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.db.base import init_db, make_engine, make_session_factory
from bot.handlers import admin, admin_branches, booking, mybookings, start
from bot.middlewares.user import UserMiddleware


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    engine = make_engine(settings.db_path)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    bot = Bot(settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    middleware = UserMiddleware(session_factory)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(mybookings.router)
    dp.include_router(admin.router)
    dp.include_router(admin_branches.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
