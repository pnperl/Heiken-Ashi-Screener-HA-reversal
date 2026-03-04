# 🚀 Free 24×7 Cloud Deployment Guide

## Files You Have
```
bot.py            ← main bot (only edit SYMBOL + INTERVAL)
.env.example      ← copy to .env and fill in your secrets
requirements.txt  ← Python dependencies
```

---

## 🔐 Secrets Management

### Local Development
```bash
cp .env.example .env
# Edit .env and fill in your real values — NEVER commit .env to Git
echo ".env" >> .gitignore
```

### On the Cloud (Render / Railway / Fly.io)
Each platform has an **Environment Variables** UI — paste your values there.
**Never put secrets in bot.py, Dockerfile, or any committed file.**

---

## ☁️ Free Cloud Options (Compared)

| Platform   | Free Tier                        | Always-on? | Best For         |
|------------|----------------------------------|------------|------------------|
| **Render** | 750 hrs/month background worker  | ✅ Yes     | Easiest setup    |
| **Railway**| $5 free credits/month            | ✅ Yes     | Fast deploys     |
| **Fly.io** | 3 shared-CPU VMs free            | ✅ Yes     | More control     |
| Replit     | Bounces after inactivity         | ❌ No      | Not suitable     |
| PythonAnywhere | 1 always-on task free        | ✅ Yes     | Python-specific  |

**Recommended: Render (easiest) or Fly.io (most reliable free tier)**

---

## ✅ Option 1 — Render (Recommended, Easiest)

### Step 1 — Push to GitHub
```bash
git init
git add bot.py requirements.txt .gitignore
# Do NOT add .env
git commit -m "initial bot"
git remote add origin https://github.com/YOUR_USERNAME/trading-bot.git
git push -u origin main
```

### Step 2 — Create a Render Background Worker
1. Go to https://render.com → **New → Background Worker**
2. Connect your GitHub repo
3. Set:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
4. Under **Environment** tab → add:
   ```
   TELEGRAM_TOKEN    = your_token
   TELEGRAM_CHAT_ID  = your_chat_id
   ```
5. Click **Deploy**

✅ Render keeps background workers running 24×7 on the free tier.
Logs are visible in the Render dashboard.

---

## ✅ Option 2 — Fly.io (Most Reliable Free Tier)

### Step 1 — Install flyctl
```bash
curl -L https://fly.io/install.sh | sh
fly auth signup
```

### Step 2 — Create a Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
```

### Step 3 — Deploy
```bash
fly launch          # follow prompts, choose free shared-cpu-1x
fly secrets set TELEGRAM_TOKEN=your_token TELEGRAM_CHAT_ID=your_chat_id
fly deploy
```

### Step 4 — Monitor
```bash
fly logs            # stream live logs
fly status          # check if running
```

---

## ✅ Option 3 — PythonAnywhere (Python-specific, dead simple)

1. Sign up at https://pythonanywhere.com (free account)
2. Upload `bot.py` and `requirements.txt` via the **Files** tab
3. Open a **Bash console**:
   ```bash
   pip install --user -r requirements.txt
   ```
4. Go to **Tasks** tab → **Always-on task** (free accounts get 1)
5. Command: `python /home/YOUR_USER/bot.py`
6. For secrets — PythonAnywhere has no native env var UI on free tier:
   ```bash
   # At the top of bot.py, add this alternative for PythonAnywhere:
   # TOKEN   = "paste_directly_here"   ← only if private repo
   # Better: use a secrets.py file and add it to .gitignore
   ```

---

## 🛡️ .gitignore (create this file in your repo root)

```
.env
*.log
__pycache__/
*.pyc
.DS_Store
secrets.py
```

---

## 🔁 Keeping It Running — Crash Recovery

Add this wrapper script `run.sh` to auto-restart on crash:
```bash
#!/bin/bash
while true; do
  echo "Starting bot at $(date)"
  python bot.py
  echo "Bot crashed. Restarting in 10s..."
  sleep 10
done
```

On Render / Railway, set **Start Command** to `bash run.sh` instead of `python bot.py`.

---

## 📊 Monitoring Tips

- All events are logged to `bot.log` (in the same folder)
- Render / Fly.io stream logs in their dashboards
- Telegram alerts tell you entry, SL trail, and exit in real time
- If you stop receiving alerts for > 1 candle interval, the bot may have crashed

---

## 🔄 Updating the Bot

```bash
# Edit bot.py locally (e.g. change SYMBOL)
git add bot.py
git commit -m "change symbol to ETH-USD"
git push
```
Render and Railway **auto-redeploy** on every push. Fly.io: run `fly deploy`.

---

## ⚡ Quick Symbol Change Examples

| What you trade     | Set SYMBOL to      |
|--------------------|--------------------|
| Bitcoin            | `BTC-USD`          |
| Ethereum           | `ETH-USD`          |
| NIFTY 50           | `^NSEI`            |
| Bank NIFTY         | `^NSEBANK`         |
| S&P 500            | `^GSPC`            |
| Apple stock        | `AAPL`             |
| Reliance (NSE)     | `RELIANCE.NS`      |

Everything else (doji threshold, strike rounding, market hours, timezone)
adjusts **automatically** — no other edits needed.
