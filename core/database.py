import asyncio
import math
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    cash INTEGER NOT NULL DEFAULT 0,
    bank INTEGER NOT NULL DEFAULT 0,
    bank_cap INTEGER NOT NULL DEFAULT 5000,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    streak INTEGER NOT NULL DEFAULT 0,
    last_daily REAL NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    lost INTEGER NOT NULL DEFAULT 0,
    commands INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS cooldowns (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    expires REAL NOT NULL,
    PRIMARY KEY (user_id, key)
);
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    qty INTEGER NOT NULL,
    PRIMARY KEY (user_id, item)
);
CREATE TABLE IF NOT EXISTS catches (
    user_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    qty INTEGER NOT NULL,
    PRIMARY KEY (user_id, item)
);
CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT,
    channels TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS blacklist (
    user_id INTEGER PRIMARY KEY,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS interactions (
    user_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, target_id, action)
);
"""

ITEM_TABLES = {"inventory", "catches"}
LEADERBOARDS = {
    "cash": "cash",
    "networth": "cash + bank",
    "level": "xp",
    "streak": "streak",
}


def level_for(xp):
    return 1 + int(math.sqrt(max(xp, 0) / 100))


def xp_for(level):
    return 100 * (level - 1) ** 2


class Database:
    def __init__(self, path):
        self.path = path
        self.conn = None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lunii-db")

    async def _call(self, fn):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, fn)

    async def connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        def op():
            conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(SCHEMA)
            self.conn = conn

        await self._call(op)

    async def close(self):
        if self.conn is not None:
            await self._call(self.conn.close)
            self.conn = None
        self._pool.shutdown(wait=False)

    async def atomic(self, fn):
        def op():
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                result = fn(self.conn)
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            self.conn.execute("COMMIT")
            return result

        return await self._call(op)

    async def fetchone(self, sql, params=()):
        def op():
            row = self.conn.execute(sql, params).fetchone()
            return dict(row) if row else None

        return await self._call(op)

    async def fetchall(self, sql, params=()):
        def op():
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

        return await self._call(op)

    async def execute(self, sql, params=()):
        def op():
            return self.conn.execute(sql, params).rowcount

        return await self._call(op)

    @staticmethod
    def _ensure(conn, uid):
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, cash, bank_cap, created) VALUES (?, ?, ?, ?)",
            (uid, config.START_CASH, config.BANK_BASE_CAP, time.time()),
        )

    async def user(self, uid):
        def fn(conn):
            self._ensure(conn, uid)
            return dict(conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone())

        return await self.atomic(fn)

    async def add_cash(self, uid, delta):
        def fn(conn):
            self._ensure(conn, uid)
            conn.execute("UPDATE users SET cash = MAX(0, cash + ?) WHERE user_id = ?", (delta, uid))
            return conn.execute("SELECT cash FROM users WHERE user_id = ?", (uid,)).fetchone()["cash"]

        return await self.atomic(fn)

    async def take_cash(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            cur = conn.execute(
                "UPDATE users SET cash = cash - ? WHERE user_id = ? AND cash >= ?", (amount, uid, amount)
            )
            return cur.rowcount > 0

        return await self.atomic(fn)

    async def transfer(self, src, dst, amount):
        def fn(conn):
            self._ensure(conn, src)
            self._ensure(conn, dst)
            cur = conn.execute(
                "UPDATE users SET cash = cash - ? WHERE user_id = ? AND cash >= ?", (amount, src, amount)
            )
            if cur.rowcount == 0:
                return False
            conn.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (amount, dst))
            return True

        return await self.atomic(fn)

    async def deposit(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            cur = conn.execute(
                "UPDATE users SET cash = cash - ?, bank = bank + ? "
                "WHERE user_id = ? AND cash >= ? AND bank + ? <= bank_cap",
                (amount, amount, uid, amount, amount),
            )
            return cur.rowcount > 0

        return await self.atomic(fn)

    async def withdraw(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            cur = conn.execute(
                "UPDATE users SET cash = cash + ?, bank = bank - ? WHERE user_id = ? AND bank >= ?",
                (amount, amount, uid, amount),
            )
            return cur.rowcount > 0

        return await self.atomic(fn)

    async def upgrade_bank(self, uid):
        def fn(conn):
            self._ensure(conn, uid)
            row = conn.execute("SELECT cash, bank_cap FROM users WHERE user_id = ?", (uid,)).fetchone()
            cap = row["bank_cap"]
            cost = int(cap * config.BANK_UPGRADE_COST_RATIO)
            new_cap = int(round(cap * config.BANK_UPGRADE_GROWTH / 100.0)) * 100
            if row["cash"] < cost:
                return False, cost, cap
            conn.execute(
                "UPDATE users SET cash = cash - ?, bank_cap = ? WHERE user_id = ?", (cost, new_cap, uid)
            )
            return True, cost, new_cap

        return await self.atomic(fn)

    async def add_bank_cap(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            conn.execute("UPDATE users SET bank_cap = bank_cap + ? WHERE user_id = ?", (amount, uid))

        await self.atomic(fn)

    async def set_cash(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            conn.execute("UPDATE users SET cash = ? WHERE user_id = ?", (max(0, amount), uid))

        await self.atomic(fn)

    async def record(self, uid, net):
        column = "won" if net > 0 else "lost"
        if net == 0:
            return

        def fn(conn):
            self._ensure(conn, uid)
            conn.execute(f"UPDATE users SET {column} = {column} + ? WHERE user_id = ?", (abs(net), uid))

        await self.atomic(fn)

    async def settle(self, uid, bet, payout):
        def fn(conn):
            self._ensure(conn, uid)
            conn.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (payout, uid))
            net = payout - bet
            if net > 0:
                conn.execute("UPDATE users SET won = won + ? WHERE user_id = ?", (net, uid))
            elif net < 0:
                conn.execute("UPDATE users SET lost = lost + ? WHERE user_id = ?", (-net, uid))
            return conn.execute("SELECT cash FROM users WHERE user_id = ?", (uid,)).fetchone()["cash"]

        return await self.atomic(fn)

    async def claim_daily(self, uid, reward, streak, interest):
        def fn(conn):
            self._ensure(conn, uid)
            conn.execute(
                "UPDATE users SET cash = cash + ?, bank = bank + ?, streak = ?, last_daily = ? WHERE user_id = ?",
                (reward, interest, streak, time.time(), uid),
            )

        await self.atomic(fn)

    async def add_xp(self, uid, amount):
        def fn(conn):
            self._ensure(conn, uid)
            row = conn.execute("SELECT xp, level FROM users WHERE user_id = ?", (uid,)).fetchone()
            xp = row["xp"] + amount
            new_level = level_for(xp)
            conn.execute(
                "UPDATE users SET xp = ?, level = ?, commands = commands + 1 WHERE user_id = ?",
                (xp, new_level, uid),
            )
            return row["level"], new_level

        return await self.atomic(fn)

    async def cooldown_left(self, uid, key):
        row = await self.fetchone("SELECT expires FROM cooldowns WHERE user_id = ? AND key = ?", (uid, key))
        if not row:
            return 0.0
        return max(0.0, row["expires"] - time.time())

    async def set_cooldown(self, uid, key, seconds):
        await self.execute(
            "INSERT INTO cooldowns (user_id, key, expires) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET expires = excluded.expires",
            (uid, key, time.time() + seconds),
        )

    async def add_item(self, table, uid, item, qty=1):
        assert table in ITEM_TABLES

        def fn(conn):
            self._ensure(conn, uid)
            conn.execute(
                f"INSERT INTO {table} (user_id, item, qty) VALUES (?, ?, ?) "
                f"ON CONFLICT(user_id, item) DO UPDATE SET qty = qty + excluded.qty",
                (uid, item, qty),
            )

        await self.atomic(fn)

    async def add_items(self, table, uid, items):
        assert table in ITEM_TABLES

        def fn(conn):
            self._ensure(conn, uid)
            for item, qty in items.items():
                conn.execute(
                    f"INSERT INTO {table} (user_id, item, qty) VALUES (?, ?, ?) "
                    f"ON CONFLICT(user_id, item) DO UPDATE SET qty = qty + excluded.qty",
                    (uid, item, qty),
                )

        await self.atomic(fn)

    async def take_item(self, table, uid, item, qty=1):
        assert table in ITEM_TABLES

        def fn(conn):
            cur = conn.execute(
                f"UPDATE {table} SET qty = qty - ? WHERE user_id = ? AND item = ? AND qty >= ?",
                (qty, uid, item, qty),
            )
            if cur.rowcount == 0:
                return False
            conn.execute(f"DELETE FROM {table} WHERE user_id = ? AND item = ? AND qty <= 0", (uid, item))
            return True

        return await self.atomic(fn)

    async def items(self, table, uid):
        assert table in ITEM_TABLES
        rows = await self.fetchall(f"SELECT item, qty FROM {table} WHERE user_id = ? AND qty > 0", (uid,))
        return {r["item"]: r["qty"] for r in rows}

    async def sell_catches(self, uid, selection, total):
        def fn(conn):
            self._ensure(conn, uid)
            for item, qty in selection.items():
                cur = conn.execute(
                    "UPDATE catches SET qty = qty - ? WHERE user_id = ? AND item = ? AND qty >= ?",
                    (qty, uid, item, qty),
                )
                if cur.rowcount == 0:
                    raise ValueError("missing")
            conn.execute("DELETE FROM catches WHERE user_id = ? AND qty <= 0", (uid,))
            conn.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (total, uid))

        try:
            await self.atomic(fn)
        except ValueError:
            return False
        return True

    async def leaderboard(self, kind, limit=10):
        expr = LEADERBOARDS[kind]
        return await self.fetchall(
            f"SELECT user_id, {expr} AS value FROM users WHERE {expr} > 0 ORDER BY value DESC LIMIT ?",
            (limit,),
        )

    async def rank(self, uid, kind):
        expr = LEADERBOARDS[kind]
        row = await self.fetchone(
            f"SELECT COUNT(*) + 1 AS rank FROM users WHERE {expr} > "
            f"(SELECT {expr} FROM users WHERE user_id = ?)",
            (uid,),
        )
        return row["rank"] if row else 0

    async def guild_settings(self):
        return await self.fetchall("SELECT guild_id, prefix, channels FROM guilds")

    async def set_prefix(self, guild_id, prefix):
        await self.execute(
            "INSERT INTO guilds (guild_id, prefix) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix",
            (guild_id, prefix),
        )

    async def set_channels(self, guild_id, channels):
        raw = ",".join(str(c) for c in sorted(channels))
        await self.execute(
            "INSERT INTO guilds (guild_id, channels) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channels = excluded.channels",
            (guild_id, raw),
        )

    async def blacklist_ids(self):
        rows = await self.fetchall("SELECT user_id FROM blacklist")
        return {r["user_id"] for r in rows}

    async def add_blacklist(self, uid, reason=""):
        await self.execute(
            "INSERT INTO blacklist (user_id, reason) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET reason = excluded.reason",
            (uid, reason),
        )

    async def remove_blacklist(self, uid):
        return await self.execute("DELETE FROM blacklist WHERE user_id = ?", (uid,))

    async def bump_interaction(self, uid, target, action):
        def fn(conn):
            conn.execute(
                "INSERT INTO interactions (user_id, target_id, action, count) VALUES (?, ?, ?, 1) "
                "ON CONFLICT(user_id, target_id, action) DO UPDATE SET count = count + 1",
                (uid, target, action),
            )
            return conn.execute(
                "SELECT count FROM interactions WHERE user_id = ? AND target_id = ? AND action = ?",
                (uid, target, action),
            ).fetchone()["count"]

        return await self.atomic(fn)

    async def totals(self):
        row = await self.fetchone("SELECT COUNT(*) AS users, COALESCE(SUM(cash + bank), 0) AS coins FROM users")
        return row or {"users": 0, "coins": 0}

    async def overview(self):
        row = await self.fetchone(
            "SELECT COUNT(*) AS users, COALESCE(SUM(cash + bank), 0) AS coins, "
            "COALESCE(SUM(won), 0) AS won, COALESCE(SUM(lost), 0) AS lost, "
            "COALESCE(SUM(commands), 0) AS commands FROM users"
        )
        caught = await self.fetchone("SELECT COALESCE(SUM(qty), 0) AS n FROM catches")
        row = dict(row or {})
        row["catches"] = caught["n"] if caught else 0
        return row
