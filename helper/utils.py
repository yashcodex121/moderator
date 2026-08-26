"""
Database utility functions for BioLink Protector Bot.
Collections:
  warnings      – per-user warn counts
  punishments   – per-chat config (mode/limit/penalty)
  whitelists    – per-chat whitelisted user IDs
  sudo_users    – global sudo user IDs
  word_blocklist– per-chat blocked words
  sticker_blocklist – per-chat blocked sticker set names
  group_registry– groups the bot is a member of
  sticker_timer – per-chat sticker auto-delete timer (seconds, 0 = off)
  sticker_mode  – per-chat sticker blocking toggle
"""

from pyrogram import Client, enums
from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    MONGO_URI,
    DEFAULT_CONFIG,
    DEFAULT_PUNISHMENT,
    DEFAULT_WARNING_LIMIT,
    OWNER_ID,
)

# ─── DB setup ────────────────────────────────────────────────────────────────
mongo_client   = AsyncIOMotorClient(MONGO_URI)
db             = mongo_client["telegram_bot_db"]

warnings_col        = db["warnings"]
punishments_col     = db["punishments"]
whitelists_col      = db["whitelists"]
sudo_col            = db["sudo_users"]
word_blocklist_col  = db["word_blocklist"]
sticker_bl_col      = db["sticker_blocklist"]
group_registry_col  = db["group_registry"]
sticker_timer_col   = db["sticker_timer"]
sticker_mode_col    = db["sticker_mode"]


# ─── Admin check ─────────────────────────────────────────────────────────────
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Return True if user is a chat admin (or creator)."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


# ─── Owner / Sudo ─────────────────────────────────────────────────────────────
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def is_sudo(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    doc = await sudo_col.find_one({"user_id": user_id})
    return bool(doc)


async def add_sudo(user_id: int):
    await sudo_col.update_one(
        {"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True
    )


async def remove_sudo(user_id: int):
    await sudo_col.delete_one({"user_id": user_id})


async def get_sudo_list() -> list:
    docs = await sudo_col.find({}).to_list(length=None)
    return [d["user_id"] for d in docs]


# ─── Config (warn limit / penalty) ───────────────────────────────────────────
async def get_config(chat_id: int):
    doc = await punishments_col.find_one({"chat_id": chat_id})
    if doc:
        return (
            doc.get("mode", "warn"),
            doc.get("limit", DEFAULT_WARNING_LIMIT),
            doc.get("penalty", DEFAULT_PUNISHMENT),
        )
    return DEFAULT_CONFIG


async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    update = {}
    if mode    is not None: update["mode"]    = mode
    if limit   is not None: update["limit"]   = limit
    if penalty is not None: update["penalty"] = penalty
    if update:
        await punishments_col.update_one(
            {"chat_id": chat_id}, {"$set": update}, upsert=True
        )


# ─── Warnings ────────────────────────────────────────────────────────────────
async def increment_warning(chat_id: int, user_id: int) -> int:
    await warnings_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$inc": {"count": 1}},
        upsert=True,
    )
    doc = await warnings_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc["count"]


async def reset_warnings(chat_id: int, user_id: int):
    await warnings_col.delete_one({"chat_id": chat_id, "user_id": user_id})


# ─── Whitelist ────────────────────────────────────────────────────────────────
async def is_whitelisted(chat_id: int, user_id: int) -> bool:
    doc = await whitelists_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(doc)


async def add_whitelist(chat_id: int, user_id: int):
    await whitelists_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True,
    )


async def remove_whitelist(chat_id: int, user_id: int):
    await whitelists_col.delete_one({"chat_id": chat_id, "user_id": user_id})


async def get_whitelist(chat_id: int) -> list:
    docs = await whitelists_col.find({"chat_id": chat_id}).to_list(length=None)
    return [d["user_id"] for d in docs]


# ─── Word blocklist ──────────────────────────────────────────────────────────
async def add_blocked_word(chat_id: int, word: str):
    w = word.lower().strip()
    await word_blocklist_col.update_one(
        {"chat_id": chat_id, "word": w},
        {"$set": {"word": w}},
        upsert=True,
    )


async def remove_blocked_word(chat_id: int, word: str):
    await word_blocklist_col.delete_one({"chat_id": chat_id, "word": word.lower().strip()})


async def get_blocked_words(chat_id: int) -> list:
    docs = await word_blocklist_col.find({"chat_id": chat_id}).to_list(length=None)
    return [d["word"] for d in docs]


async def is_word_blocked(chat_id: int, text: str) -> str | None:
    """Return the first matching blocked word found in text, else None."""
    words = await get_blocked_words(chat_id)
    text_lower = text.lower()
    for w in words:
        if w in text_lower:
            return w
    return None


# ─── Sticker blocklist ───────────────────────────────────────────────────────
async def block_sticker_set(chat_id: int, set_name: str):
    await sticker_bl_col.update_one(
        {"chat_id": chat_id, "set_name": set_name},
        {"$set": {"set_name": set_name}},
        upsert=True,
    )


async def unblock_sticker_set(chat_id: int, set_name: str):
    await sticker_bl_col.delete_one({"chat_id": chat_id, "set_name": set_name})


async def get_blocked_sticker_sets(chat_id: int) -> list:
    docs = await sticker_bl_col.find({"chat_id": chat_id}).to_list(length=None)
    return [d["set_name"] for d in docs]


async def is_sticker_blocked(chat_id: int, set_name: str) -> bool:
    doc = await sticker_bl_col.find_one({"chat_id": chat_id, "set_name": set_name})
    return bool(doc)


# ─── Sticker auto-delete timer ───────────────────────────────────────────────
async def set_sticker_timer(chat_id: int, seconds: int):
    """0 means timer is off."""
    await sticker_timer_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"seconds": seconds}},
        upsert=True,
    )


async def get_sticker_timer(chat_id: int) -> int:
    doc = await sticker_timer_col.find_one({"chat_id": chat_id})
    return doc["seconds"] if doc else 0


# ─── Sticker mode (on / off) ─────────────────────────────────────────────────
async def set_sticker_mode(chat_id: int, enabled: bool):
    """enabled=False means all stickers are deleted immediately."""
    await sticker_mode_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled}},
        upsert=True,
    )


async def get_sticker_mode(chat_id: int) -> bool:
    """Returns True (stickers allowed) by default."""
    doc = await sticker_mode_col.find_one({"chat_id": chat_id})
    if doc is None:
        return True
    return doc.get("enabled", True)


# ─── Group registry ───────────────────────────────────────────────────────────
async def register_group(chat_id: int, title: str = ""):
    await group_registry_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "title": title}},
        upsert=True,
    )


async def unregister_group(chat_id: int):
    await group_registry_col.delete_one({"chat_id": chat_id})


async def get_all_groups() -> list:
    docs = await group_registry_col.find({}).to_list(length=None)
    return [d["chat_id"] for d in docs]
