# -*- coding: utf-8 -*-
import asyncio
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip().rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")
if not WEB_APP_URL:
    raise RuntimeError("WEB_APP_URL is not set in .env")

router = Router()

WELCOME = (
    "💸 <b>Игра: Потрать $1,000,000 за 5 минут</b>\n\n"
    "Открывай мини‑приложение и попробуй потратить миллион быстрее всех! "
    "Собирай чек, покупай предметы и попади в топ.\n\n"
    "⏱️ На всё — 5 минут. Удачи!"
)

@router.message(CommandStart())
async def cmd_start(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Играть",
            web_app=WebAppInfo(url=f"{WEB_APP_URL}/")
        )
    ]])
    await msg.answer(WELCOME, reply_markup=kb, parse_mode="HTML")


async def main():
    dp = Dispatcher()
    dp.include_router(router)
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    print("Bot started. Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
