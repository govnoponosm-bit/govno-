from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from database import Database, Subscription

ACTIVE_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}


async def has_required_subscriptions(db: Database) -> bool:
    return bool(await db.list_subscriptions(active_only=True))


async def get_missing_subscriptions(
    bot: Bot, db: Database, user_id: int
) -> list[Subscription]:
    subs = await db.list_subscriptions(active_only=True)
    if not subs:
        return []

    missing: list[Subscription] = []
    for sub in subs:
        chat_id = sub.chat_id
        if chat_id.startswith("@"):
            chat_id = chat_id
        elif chat_id.lstrip("-").isdigit():
            chat_id = int(chat_id)
        else:
            missing.append(sub)
            continue

        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ACTIVE_STATUSES:
                missing.append(sub)
        except TelegramBadRequest:
            missing.append(sub)

    return missing
