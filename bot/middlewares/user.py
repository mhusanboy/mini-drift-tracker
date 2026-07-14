from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.models import User


class UserMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["session_factory"] = self.session_factory
        tg_user = data.get("event_from_user")
        user = None
        if tg_user is not None:
            async with self.session_factory() as session:
                user = await session.get(User, tg_user.id)
        data["user"] = user
        data["lang"] = user.language if user else "ru"
        return await handler(event, data)
