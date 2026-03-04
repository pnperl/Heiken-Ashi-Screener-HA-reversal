# Heiken-Ashi-Screener-HA-reversal
Heiken Ashi Screener HA reversal
Imagine you're staring at a price chart all day, watching for a specific pattern, then texting yourself "buy now" or "sell now". The bot does exactly that — automatically, 24×7, without you watching.
Upon activation, the bot automatically detects your selected SYMBOL to configure its core trading logic based on specific asset profiles. For BTC, it identifies the asset as a Crypto operating in the UTC timezone with a 24/7 "Always open" market. To account for Bitcoin's high volatility, it sets a tighter signal sensitivity of 0.15 and rounds strike prices to the nearest ₹500. 
Conversely, for NIFTY, the bot recognizes it as an Indian Index following Asia/Kolkata time. It adheres to standard National Stock Exchange (NSE) hours from 9:15 am to 3:30 pm. The bot applies a smoother sensitivity of 0.20 and uses a precise strike price rounding of ₹50 to match the standard Nifty option chain increments.
