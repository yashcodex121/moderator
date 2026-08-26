# Copyright (C) @TheSmartBisnu
# Copy this file to config.py and fill in your real values.

import re

# ─── Telegram API credentials ────────────────────────────────────────────────
API_ID   = "12345678"           # Your Telegram API ID  (from my.telegram.org)
API_HASH = "your_api_hash"      # Your Telegram API Hash
BOT_TOKEN = "your_bot_token"    # Your Bot Token (from @BotFather)

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_URI = "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"

# ─── Owner / Sudo ─────────────────────────────────────────────────────────────
OWNER_ID       = 123456789      # Your Telegram user ID (integer, from @userinfobot)
OWNER_USERNAME = "YourUsername" # Without @
LOG_CHAT_ID    = None           # Log channel/group ID (int) or None to disable

# ─── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT    = "mute"  # "mute" or "ban"
DEFAULT_CONFIG        = ("warn", DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT)

# ─── URL pattern (bio + message text) ────────────────────────────────────────
URL_PATTERN = re.compile(
    r'(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+\-]*)*',
    re.IGNORECASE
)
