from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from database import Database

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    total: int
    sent: int
    failed: int
    blocked: int


async def broadcast_post(
    bot: Bot,
    db: Database,
    from_chat_id: int,
    message_id: int,
    *,
    delay_sec: float = 0.05,
) -> BroadcastResult:
    user_ids = await db.list_broadcast_user_ids()
    sent = 0
    failed = 0
    blocked = 0

    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
            await db.mark_user_blocked(user_id)
        except TelegramBadRequest as e:
            logger.warning("Рассылка: ошибка для user_id=%s: %s", user_id, e)
            failed += 1
        except Exception as e:
            logger.exception("Рассылка: неожиданная ошибка для user_id=%s: %s", user_id, e)
            failed += 1

        if delay_sec:
            await asyncio.sleep(delay_sec)

    return BroadcastResult(
        total=len(user_ids),
        sent=sent,
        failed=failed,
        blocked=blocked,
    )
