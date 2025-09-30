# -*- coding: utf-8 -*-
import os
import time
import json
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from db import init_db, get_db
from web.utils_verify import verify_telegram_init_data

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN must be set in environment for initData verification")

app = FastAPI(title="Spend Million Game")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WebApp opens in Telegram, origin control is not strict here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
async def _startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def _now() -> int:
    return int(time.time())

@app.post("/api/start")
async def api_start(request: Request):
    body = await request.json()
    init_data = body.get("initData", "")
    if not verify_telegram_init_data(init_data, BOT_TOKEN):
        # For dev you can comment this to allow local testing
        raise HTTPException(status_code=401, detail="Invalid initData")

    # parse user from initDataUnsafe (client sends it too for convenience)
    user = body.get("user") or {}
    user_id = int(user.get("id", 0))
    username = user.get("username", "")

    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user")

    now = _now()
    expires = now + 300  # 5 minutes
    async with await get_db() as db:
        # start new session if none active
        # find last session that is not finished and not expired
        async with db.execute(
            "SELECT id, expires_at, finished FROM sessions WHERE user_id=? ORDER BY started_at DESC LIMIT 1",
            (user_id, )
        ) as cur:
            row = await cur.fetchone()

        if row and row[2] == 0 and row[1] > now:
            session_id = row[0]
        else:
            await db.execute(
                "INSERT INTO sessions(user_id, username, started_at, expires_at, balance_start, spent, finished) VALUES(?, ?, ?, ?, 1000000, 0, 0)",
                (user_id, username, now, expires)
            )
            await db.commit()
            session_id = (await db.execute("SELECT last_insert_rowid()")).cursor.lastrowid

        # fetch snapshot
        async with db.execute("SELECT spent, expires_at FROM sessions WHERE id=?", (session_id,)) as cur2:
            row2 = await cur2.fetchone()

        return JSONResponse({
            "ok": True,
            "session_id": session_id,
            "spent": row2[0],
            "expires_at": row2[1],
            "now": now
        })

@app.post("/api/spend")
async def api_spend(request: Request):
    body = await request.json()
    init_data = body.get("initData", "")
    if not verify_telegram_init_data(init_data, BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid initData")

    user = body.get("user") or {}
    user_id = int(user.get("id", 0))
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user")

    session_id = int(body.get("session_id", 0))
    item = str(body.get("item", "")).strip()[:64]
    amount = int(body.get("amount", 0))

    if session_id <= 0 or not item or amount <= 0:
        raise HTTPException(status_code=400, detail="Bad params")

    now = _now()
    async with await get_db() as db:
        async with db.execute("SELECT user_id, spent, expires_at, finished, balance_start FROM sessions WHERE id=?", (session_id,)) as cur:
            s = await cur.fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        if s[0] != user_id:
            raise HTTPException(status_code=403, detail="Foreign session")
        if s[3] == 1 or now >= s[2]:
            raise HTTPException(status_code=400, detail="Session finished")

        spent = s[1]
        balance_start = s[4]
        if spent + amount > balance_start:
            amount = max(0, balance_start - spent)  # clamp to remaining
        if amount == 0:
            return JSONResponse({"ok": False, "reason": "No balance left"})

        await db.execute(
            "INSERT INTO spends(session_id, item, amount, ts) VALUES(?, ?, ?, ?)",
            (session_id, item, amount, now)
        )
        new_spent = spent + amount
        finished = 1 if (new_spent >= balance_start or now >= s[2]) else 0
        await db.execute(
            "UPDATE sessions SET spent=?, finished=? WHERE id=?",
            (new_spent, finished, session_id)
        )
        await db.commit()

        return JSONResponse({
            "ok": True,
            "spent": new_spent,
            "remaining": max(0, balance_start - new_spent),
            "finished": finished
        })

@app.post("/api/finish")
async def api_finish(request: Request):
    body = await request.json()
    init_data = body.get("initData", "")
    if not verify_telegram_init_data(init_data, BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid initData")

    user = body.get("user") or {}
    user_id = int(user.get("id", 0))
    session_id = int(body.get("session_id", 0))
    now = _now()

    async with await get_db() as db:
        async with db.execute("SELECT user_id, expires_at, spent, finished, balance_start FROM sessions WHERE id=?", (session_id,)) as cur:
            s = await cur.fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        if s[0] != user_id:
            raise HTTPException(status_code=403, detail="Foreign session")
        finished = 1 if (now >= s[1] or s[2] >= s[4]) else s[3]
        await db.execute("UPDATE sessions SET finished=? WHERE id=?", (finished, session_id))
        await db.commit()
        return JSONResponse({"ok": True, "finished": finished})

@app.get("/api/leaderboard")
async def api_leaderboard():
    async with await get_db() as db:
        async with db.execute(
            "SELECT username, spent FROM sessions WHERE finished=1 ORDER BY spent DESC, started_at ASC LIMIT 20"
        ) as cur:
            rows = await cur.fetchall()
    items = [{"username": r[0] or "anon", "spent": r[1]} for r in rows]
    return JSONResponse({"ok": True, "items": items})
