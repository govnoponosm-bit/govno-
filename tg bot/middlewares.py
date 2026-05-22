import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from config import Settings
from database import Database

logger = logging.getLogger(__name__)


class InjectMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        data["db"] = self.db
        data["is_admin"] = bool(user and user.id in self.settings.admin_ids)

        if user and not user.is_bot:
            await self.db.upsert_user(user.id)

        return await handler(event, data)