# -*- coding: utf-8 -*-
import aiosqlite
import asyncio
from typing import Optional

DB_PATH = "game.db"

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    started_at INTEGER NOT NULL,   -- epoch seconds
    expires_at INTEGER NOT NULL,   -- epoch seconds = started_at + 300
    balance_start INTEGER NOT NULL DEFAULT 1000000,
    spent INTEGER NOT NULL DEFAULT 0,
    finished INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS spends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    amount INTEGER NOT NULL,
    ts INTEGER NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_spends_session ON spends(session_id);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def get_db():
    return await aiosqlite.connect(DB_PATH)
