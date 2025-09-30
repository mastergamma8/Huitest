# Spend $1,000,000 in 5 minutes — Telegram WebApp + Bot (aiogram + FastAPI)

This project contains:
- **bot.py** — aiogram bot with a button that opens the mini-app (Telegram WebApp).
- **web/** — FastAPI app serving the game UI and API.
- **SQLite** storage via `aiosqlite`.

## Quickstart (local/dev)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then edit BOT_TOKEN and WEB_APP_URL
```

### Run web (FastAPI)
```bash
uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload
```
### Run bot (aiogram)
```bash
python bot.py
```

Open the bot in Telegram and press **Play**. The WebApp must be reachable via **HTTPS** from the URL set in `WEB_APP_URL`.

## Deploy notes
- Use a VPS (e.g. Heloki/Hetzner), reverse-proxy (Caddy/Nginx) to get HTTPS.
- Or use a tunnel (Cloudflare Tunnel / ngrok) to expose your local dev server with HTTPS.
- For managed platforms (Railway/Render/Fly/Deta): run web as a web service and bot as a worker.
