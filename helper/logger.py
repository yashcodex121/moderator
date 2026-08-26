"""
Logger for BioLink Protector Bot.

• Console  – Python logging at INFO level (structured, with timestamp)
• Telegram – Quote-style message sent to LOG_CHAT_ID (if configured)

Usage:
    from helper.logger import log

    await log(client, "Bot started", level="INFO")
    await log(client, f"Group added: {title}", level="INFO", chat_id=cid)
    await log(client, f"Deleted message by {user}", level="WARN",  chat_id=cid)
"""

import logging
from datetime import datetime, timezone

from config import LOG_CHAT_ID

# ─── Console logger ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
_log = logging.getLogger("BioBot")

# ─── Level → emoji map ───────────────────────────────────────────────────────
_EMOJI = {
    "INFO":  "ℹ️",
    "WARN":  "⚠️",
    "ERROR": "❌",
    "START": "🟢",
    "JOIN":  "➕",
    "LEFT":  "➖",
    "DEL":   "🗑️",
    "BAN":   "🔨",
    "MUTE":  "🔇",
    "UNMUTE":"🔊",
    "UNBAN": "✅",
    "CFG":   "⚙️",
    "SUDO":  "👑",
    "BROAD": "📢",
    "PURGE": "🧹",
    "ABUSE": "🚫",
    "STICK": "🎭",
}


async def log(
    client,
    text: str,
    *,
    level: str = "INFO",
    chat_id: int | None = None,
    extra: dict | None = None,
):
    """
    Log an event.

    Parameters
    ----------
    client   : Pyrogram Client instance
    text     : Human-readable description of the event
    level    : One of the keys in _EMOJI (defaults to "INFO")
    chat_id  : The group/chat this event belongs to (optional)
    extra    : Additional key→value pairs shown in the Telegram log
    """
    level = level.upper()
    emoji = _EMOJI.get(level, "📋")
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # ── Console ──
    console_msg = text
    if chat_id:
        console_msg += f" | chat={chat_id}"
    if extra:
        console_msg += " | " + " | ".join(f"{k}={v}" for k, v in extra.items())
    _log.info(console_msg)

    # ── Telegram ──
    if not LOG_CHAT_ID:
        return

    lines = [
        f"{emoji} **[{level}]** `{now}`",
        f"📝 {text}",
    ]
    if chat_id:
        lines.append(f"💬 **Chat ID:** `{chat_id}`")
    if extra:
        for k, v in extra.items():
            lines.append(f"• **{k}:** `{v}`")

    tg_text = "\n".join(lines)

    try:
        await client.send_message(
            LOG_CHAT_ID,
            tg_text,
            # quote-style: disable web preview, use monospace-friendly markdown
            disable_web_page_preview=True,
        )
    except Exception as e:
        _log.error(f"Failed to send log to Telegram: {e}")
