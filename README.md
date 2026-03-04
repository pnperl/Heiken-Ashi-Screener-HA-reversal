# Heiken-Ashi-Screener-HA-reversal
Heiken Ashi Screener HA reversal
Imagine you're staring at a price chart all day, watching for a specific pattern, then texting yourself "buy now" or "sell now". The bot does exactly that — automatically, 24×7, without you watching.
Upon activation, the bot automatically detects your selected SYMBOL to configure its core trading logic based on specific asset profiles. For BTC, it identifies the asset as a Crypto operating in the UTC timezone with a 24/7 "Always open" market. To account for Bitcoin's high volatility, it sets a tighter signal sensitivity of 0.15 and rounds strike prices to the nearest ₹500. 
Conversely, for NIFTY, the bot recognizes it as an Indian Index following Asia/Kolkata time. It adheres to standard National Stock Exchange (NSE) hours from 9:15 am to 3:30 pm. The bot applies a smoother sensitivity of 0.20 and uses a precise strike price rounding of ₹50 to match the standard Nifty option chain increments.

**Setting Up the Bot on Old Android Phone**
Open Termux and type these commands one by one:

**Step 1 — Download code from GitHub**
```bash
git clone https://github.com/YOUR_USERNAME/trading-bot.git
```
Replace `YOUR_USERNAME` and `trading-bot` with your actual GitHub username and repo name.

**Step 2 — Go into the folder**
```bash
cd trading-bot
```

**Step 3 — Install dependencies**
```bash
pip install yfinance pandas numpy requests python-dotenv
```

**Step 4 — Create your secrets file**
```bash
nano .env
```
Type this:
```
TELEGRAM_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```
Press **Ctrl+X → Y → Enter** to save.

**Step 5 — Create the auto-restart script**
```bash
nano run.sh
```
Type this:
```bash
#!/bin/bash
while true; do
  python bot.py >> bot.log 2>&1
  sleep 10
done
```
Press **Ctrl+X → Y → Enter** to save.

**Step 6 — Run it**
```bash
nohup bash run.sh &
```

**Step 7 — Confirm it's working**
```bash
cat bot.log
```
You should see the bot startup message. ✅

---

That's it. Bot is now running 24×7.

> 💡 **Every time you update code on GitHub**, just run:
> ```bash
> pkill python
> git pull
> nohup bash run.sh &
> ```
