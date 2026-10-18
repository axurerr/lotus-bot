import aiosqlite
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "lotus.db"
DB_PATH.parent.mkdir(exist_ok=True)


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Настройки сервера
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                start_role_id TEXT,
                log_channel_id TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        # Исключаемые роли (не сохраняются при выходе)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS excluded_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(guild_id, role_id)
            )
        """)

        # Сохранённые роли пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(guild_id, user_id, role_id)
            )
        """)

        # Логи действий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                role_id TEXT,
                details TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        await db.commit()
    print("✅ База данных инициализирована")


# ===== Guild Settings =====
async def get_guild_settings(guild_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_start_role(guild_id: int, role_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, start_role_id, updated_at)
            VALUES (?, ?, strftime('%s', 'now'))
            ON CONFLICT(guild_id) DO UPDATE SET
                start_role_id = excluded.start_role_id,
                updated_at = strftime('%s', 'now')
        """, (str(guild_id), str(role_id) if role_id else None))
        await db.commit()


async def set_log_channel(guild_id: int, channel_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, log_channel_id, updated_at)
            VALUES (?, ?, strftime('%s', 'now'))
            ON CONFLICT(guild_id) DO UPDATE SET
                log_channel_id = excluded.log_channel_id,
                updated_at = strftime('%s', 'now')
        """, (str(guild_id), str(channel_id) if channel_id else None))
        await db.commit()


# ===== Excluded Roles =====
async def get_excluded_roles(guild_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role_id FROM excluded_roles WHERE guild_id = ?", (str(guild_id),)
        ) as cursor:
            rows = await cursor.fetchall()
            return [int(r[0]) for r in rows]


async def add_excluded_role(guild_id: int, role_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO excluded_roles (guild_id, role_id) VALUES (?, ?)",
            (str(guild_id), str(role_id))
        )
        await db.commit()
        return cursor.rowcount > 0


async def remove_excluded_role(guild_id: int, role_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM excluded_roles WHERE guild_id = ? AND role_id = ?",
            (str(guild_id), str(role_id))
        )
        await db.commit()
        return cursor.rowcount > 0


async def clear_excluded_roles(guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM excluded_roles WHERE guild_id = ?", (str(guild_id),)
        )
        await db.commit()
        return cursor.rowcount


# ===== User Roles Persistence =====
async def save_user_roles(guild_id: int, user_id: int, role_ids: list[int]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_roles WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        if role_ids:
            await db.executemany(
                "INSERT INTO user_roles (guild_id, user_id, role_id) VALUES (?, ?, ?)",
                [(str(guild_id), str(user_id), str(rid)) for rid in role_ids]
            )
        await db.commit()


async def get_user_roles(guild_id: int, user_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role_id FROM user_roles WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        ) as cursor:
            rows = await cursor.fetchall()
            return [int(r[0]) for r in rows]


async def delete_user_roles(guild_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_roles WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        await db.commit()
        return cursor.rowcount


# ===== Action Logs =====
async def log_action(
    guild_id: int,
    user_id: int,
    action_type: str,
    role_id: int | None = None,
    details: str | None = None
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO action_logs (guild_id, user_id, action_type, role_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (str(guild_id), str(user_id), action_type, str(role_id) if role_id else None, details))
        await db.commit()


async def get_recent_logs(guild_id: int, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM action_logs WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?
        """, (str(guild_id), limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]