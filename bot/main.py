import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.config import get_settings
from bot.db.base import init_db, make_engine, make_session_factory
from bot.handlers import (
    admin,
    admin_bookings,
    admin_dayoffs,
    admin_service,
    booking,
    mybookings,
    start,
)
from bot.middlewares.user import UserMiddleware

DEFAULT_COMMANDS = [
    BotCommand(command="start", description="Boshlash / Начать"),
    BotCommand(command="mybookings", description="Mening bronlarim / Мои брони"),
]
ADMIN_COMMANDS = DEFAULT_COMMANDS + [
    BotCommand(command="admin", description="Админ-панель / Admin panel"),
    BotCommand(command="service", description="Настройки / Sozlamalar"),
    BotCommand(command="stats", description="Статистика / Statistika"),
    BotCommand(command="users", description="Пользователи / Foydalanuvchilar"),
    BotCommand(command="export", description="Excel"),
]


async def setup_commands(bot: Bot, admin_ids) -> None:
    await bot.set_my_commands(DEFAULT_COMMANDS, scope=BotCommandScopeDefault())
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as exc:  # noqa: BLE001 - admin may not have opened the bot yet
            logging.warning("Could not set admin commands for %s: %s", admin_id, exc)


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
    dp.include_router(admin_service.router)
    dp.include_router(admin_bookings.router)
    dp.include_router(admin_dayoffs.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_commands(bot, settings.admin_ids)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
