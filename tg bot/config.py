import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    db_path: str = "bot.db"


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if part.isdigit():
            ids.add(int(part))
    return frozenset(ids)


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "BOT_TOKEN не задан. Добавьте в .env или в Replit → Secrets."
        )

    admin_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = _parse_admin_ids(admin_raw)
    if not admin_ids:
        raise ValueError(
            "ADMIN_IDS не задан (числовой Telegram ID через запятую). "
            "На Replit: Tools → Secrets → ADMIN_IDS=123456789"
        )

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=os.getenv("DB_PATH", "bot.db"),
    )
