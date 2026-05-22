from __future__ import annotations

import re
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Chat, Message
from aiogram.types import MessageOriginChannel

ALLOWED_CHAT_TYPES = {ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP}

BOT_ADMIN_STATUSES = {
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


class ChannelResolveError(Exception):
    pass


class InvalidLinkError(ChannelResolveError):
    pass


class BotNotAdminError(ChannelResolveError):
    pass


def _normalize_url(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    if text.startswith(("t.me/", "telegram.me/")):
        return f"https://{text}"
    return None


def parse_public_link(text: str) -> str | int | None:
    """@username, numeric id, or public t.me/username link."""
    text = text.strip()

    if text.startswith("@"):
        return text

    if text.lstrip("-").isdigit():
        return int(text)

    url = _normalize_url(text)
    if not url:
        return None

    path = urlparse(url).path.strip("/")
    if not path or path.startswith("+") or path.startswith("joinchat"):
        return None

    username = path.split("/")[0]
    if re.fullmatch(r"[\w]{4,}", username):
        return f"@{username}"
    return None


def _forwarded_chat(message: Message) -> Chat | None:
    if message.forward_from_chat:
        return message.forward_from_chat
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        return origin.chat
    return None


async def resolve_channel_from_message(bot: Bot, message: Message) -> tuple[Chat, str | None]:
    """
    Resolve channel/chat from a link or forwarded channel post.
    Returns (chat, invite_link for subscription button).
    """
    invite_link: str | None = None
    raw = (message.text or "").strip()

    forwarded = _forwarded_chat(message)
    if forwarded:
        chat = forwarded
        if raw:
            invite_link = _normalize_url(raw) or raw
    elif raw:
        invite_link = _normalize_url(raw) or raw
        identifier = parse_public_link(raw)
        if identifier is None:
            raise InvalidLinkError(
                "Не удалось распознать ссылку. Отправьте публичную ссылку "
                "(https://t.me/username или @username) либо перешлите сообщение "
                "из приватного канала, если бот уже добавлен туда админом."
            )
        try:
            chat = await bot.get_chat(identifier)
        except TelegramBadRequest as e:
            raise InvalidLinkError(
                "Канал не найден. Проверьте ссылку и что бот добавлен в канал/чат."
            ) from e
    else:
        raise InvalidLinkError("Отправьте ссылку на канал или чат.")

    if chat.type not in ALLOWED_CHAT_TYPES:
        raise InvalidLinkError("Поддерживаются только каналы и групповые чаты.")

    me = await bot.get_me()
    try:
        member = await bot.get_chat_member(chat.id, me.id)
    except TelegramBadRequest as e:
        raise BotNotAdminError(
            "Бот не добавлен в этот канал/чат. Сначала сделайте бота администратором."
        ) from e

    if member.status not in BOT_ADMIN_STATUSES:
        raise BotNotAdminError(
            "Бот не является администратором в этом канале/чате. "
            "Назначьте бота админом, затем повторите."
        )

    if not invite_link and chat.username:
        invite_link = f"https://t.me/{chat.username}"

    if not invite_link:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except TelegramBadRequest:
            pass

    return chat, invite_link


def chat_id_for_db(chat: Chat) -> str:
    return str(chat.id)
