from __future__ import annotations

import time
import aiosqlite
from dataclasses import dataclass
from typing import Optional


@dataclass
class Movie:
    id: int
    code: str
    title: str
    description: str
    link: str


@dataclass
class Subscription:
    id: int
    chat_id: str
    title: str
    invite_link: Optional[str]
    expires_at: Optional[int] = None  # None = бессрочно

    @property
    def is_permanent(self) -> bool:
        return self.expires_at is None

    @property
    def is_active(self) -> bool:
        if self.expires_at is None:
            return True
        return int(time.time()) < self.expires_at


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    link TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    invite_link TEXT,
                    expires_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id INTEGER PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    is_blocked INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            await self._migrate(db)
            await db.commit()

    async def _migrate(self, db: aiosqlite.Connection) -> None:
        async with db.execute("PRAGMA table_info(subscriptions)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "expires_at" not in cols:
            await db.execute(
                "ALTER TABLE subscriptions ADD COLUMN expires_at INTEGER"
            )

        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bot_users'"
        ) as cur:
            if not await cur.fetchone():
                await db.execute(
                    """
                    CREATE TABLE bot_users (
                        user_id INTEGER PRIMARY KEY,
                        created_at INTEGER NOT NULL,
                        is_blocked INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )

    def _row_to_subscription(self, r: aiosqlite.Row) -> Subscription:
        return Subscription(
            id=r["id"],
            chat_id=r["chat_id"],
            title=r["title"],
            invite_link=r["invite_link"],
            expires_at=r["expires_at"],
        )

    async def add_movie(
        self, code: str, title: str, description: str, link: str
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO movies (code, title, description, link)
                VALUES (?, ?, ?, ?)
                """,
                (code.strip().upper(), title.strip(), description.strip(), link.strip()),
            )
            await db.commit()

    async def update_movie(
        self, movie_id: int, title: str, description: str, link: str
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE movies SET title = ?, description = ?, link = ?
                WHERE id = ?
                """,
                (title.strip(), description.strip(), link.strip(), movie_id),
            )
            await db.commit()

    async def delete_movie(self, movie_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            await db.commit()

    async def get_movie_by_code(self, code: str) -> Optional[Movie]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM movies WHERE code = ? COLLATE NOCASE",
                (code.strip().upper(),),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return Movie(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            description=row["description"],
            link=row["link"],
        )

    async def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM movies WHERE id = ?", (movie_id,)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return Movie(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            description=row["description"],
            link=row["link"],
        )

    async def list_movies(self) -> list[Movie]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM movies ORDER BY code ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            Movie(
                id=r["id"],
                code=r["code"],
                title=r["title"],
                description=r["description"],
                link=r["link"],
            )
            for r in rows
        ]

    async def add_subscription(
        self,
        chat_id: str,
        title: str,
        invite_link: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO subscriptions (chat_id, title, invite_link, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = excluded.title,
                    invite_link = excluded.invite_link,
                    expires_at = excluded.expires_at
                """,
                (chat_id.strip(), title.strip(), invite_link, expires_at),
            )
            await db.commit()

    async def delete_subscription(self, sub_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
            await db.commit()

    async def list_subscriptions(self, active_only: bool = False) -> list[Subscription]:
        query = "SELECT * FROM subscriptions"
        params: tuple = ()
        if active_only:
            query += " WHERE expires_at IS NULL OR expires_at > ?"
            params = (int(time.time()),)
        query += " ORDER BY id ASC"

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [self._row_to_subscription(r) for r in rows]

    async def get_subscription(self, sub_id: int) -> Optional[Subscription]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM subscriptions WHERE id = ?", (sub_id,)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_subscription(row)

    async def upsert_user(self, user_id: int) -> None:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO bot_users (user_id, created_at, is_blocked)
                VALUES (?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                    is_blocked = 0,
                    created_at = excluded.created_at
                """,
                (user_id, now),
            )
            await db.commit()

    async def mark_user_blocked(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE bot_users SET is_blocked = 1 WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()

    async def count_broadcast_users(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM bot_users WHERE is_blocked = 0"
            ) as cursor:
                row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def list_broadcast_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT user_id FROM bot_users WHERE is_blocked = 0"
            ) as cursor:
                rows = await cursor.fetchall()
        return [int(r[0]) for r in rows]
