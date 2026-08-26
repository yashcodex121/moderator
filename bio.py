"""
BioLink Protector Bot  –  Enhanced Edition
Author  : Bisnu Ray  |  https://t.me/BisnuRay
Channel : https://t.me/itsSmartDev

Features
--------
• Bio-link detection  (warn / mute / ban)
• Message-link detection  (same pipeline)
• Abuse / word blocklist   (/add, /addlist)
• Sticker blocklist        (/block, /blocklist)
• Sticker mode             (/sticker off|on)
• Sticker auto-delete timer(/settimer <sec>)
• Purge                    (/purge, /purgeall)
• Broadcast                (/broadcast)
• Sudo management          (/addsudo, /rmsudo, /sudolist)
• Whitelist                (/free, /unfree, /freelist)
• Config                   (/config)
• Colourful banners with inline buttons (auto-delete after 40 s)
• Telegram + console logger (INFO level)
"""

import asyncio
from datetime import datetime, timezone

from pyrogram import Client, filters, errors
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    Message,
)

from config import (
    API_ID, API_HASH, BOT_TOKEN,
    OWNER_ID, OWNER_USERNAME, LOG_CHAT_ID,
    URL_PATTERN,
)
from helper.utils import (
    is_admin, is_owner, is_sudo,
    add_sudo, remove_sudo, get_sudo_list,
    get_config, update_config,
    increment_warning, reset_warnings,
    is_whitelisted, add_whitelist, remove_whitelist, get_whitelist,
    add_blocked_word, remove_blocked_word, get_blocked_words, is_word_blocked,
    block_sticker_set, unblock_sticker_set,
    get_blocked_sticker_sets, is_sticker_blocked,
    set_sticker_timer, get_sticker_timer,
    set_sticker_mode, get_sticker_mode,
    register_group, unregister_group, get_all_groups,
)
from helper.logger import log

# ─────────────────────────────────────────────────────────────────────────────
app = Client(
    "biolink_protector_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def auto_delete(msg: Message, delay: int = 40):
    """Delete a message after `delay` seconds silently."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


def _banner_kb(*rows):
    """Build an InlineKeyboardMarkup from a list of button-row lists."""
    return InlineKeyboardMarkup(list(rows))


async def send_banner(chat, text: str, kb: InlineKeyboardMarkup, reply_to=None):
    """Send a banner and schedule auto-delete after 40 s."""
    if reply_to:
        sent = await reply_to.reply_text(text, reply_markup=kb)
    else:
        sent = await chat.send_message(text, reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    return sent


# ══════════════════════════════════════════════════════════════════════════════
#  BOT STARTUP / GROUP TRACKING
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.new_chat_members)
async def on_bot_added(client: Client, message: Message):
    bot = await client.get_me()
    for member in message.new_chat_members:
        if member.id == bot.id:
            chat = message.chat
            await register_group(chat.id, chat.title or "")
            await log(client, f"Bot added to group: {chat.title}",
                      level="JOIN", chat_id=chat.id,
                      extra={"title": chat.title, "id": chat.id})
            kb = _banner_kb(
                [InlineKeyboardButton("➕ Add to Another Group",
                                      url=f"https://t.me/{bot.username}?startgroup=true")],
                [InlineKeyboardButton("🛠️ Support", url="https://t.me/itsSmartDev"),
                 InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME}")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            )
            sent = await client.send_message(
                chat.id,
                "**🛡️ BioLink Protector activated!**\n\n"
                "I'll protect this group from bio links, abusive words, blocked stickers & more.\n"
                "Use /help to see all commands.",
                reply_markup=kb,
            )
            asyncio.create_task(auto_delete(sent, 40))


@app.on_message(filters.left_chat_member)
async def on_bot_removed(client: Client, message: Message):
    bot = await client.get_me()
    if message.left_chat_member.id == bot.id:
        chat = message.chat
        await unregister_group(chat.id)
        await log(client, f"Bot removed from group: {chat.title}",
                  level="LEFT", chat_id=chat.id,
                  extra={"title": chat.title, "id": chat.id})


# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    bot = await client.get_me()
    add_url = f"https://t.me/{bot.username}?startgroup=true"
    text = (
        "**✨ BioLink Protector Bot ✨**\n\n"
        "🛡️ Protecting your groups from bio links, abusive words & more.\n\n"
        "**🔹 Features:**\n"
        "  • Bio & message link detection\n"
        "  • Word / abuse blocklist\n"
        "  • Sticker blocklist & timer\n"
        "  • Purge, broadcast, sudo system\n\n"
        "Use /help for all commands."
    )
    kb = _banner_kb(
        [InlineKeyboardButton("➕ Add Me to Group", url=add_url)],
        [InlineKeyboardButton("🛠️ Support", url="https://t.me/itsSmartDev"),
         InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    )
    await client.send_message(message.chat.id, text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    text = (
        "**🛠️ All Commands**\n\n"
        "**🔗 Bio / Link Protection**\n"
        "`/config` – set warn limit & punishment\n"
        "`/free` – whitelist a user\n"
        "`/unfree` – remove from whitelist\n"
        "`/freelist` – show whitelisted users\n\n"
        "**🚫 Word Blocklist** _(owner/sudo only)_\n"
        "`/add <word>` or reply to a message\n"
        "`/addlist` – show blocked words\n\n"
        "**🎭 Sticker Controls** _(admin only)_\n"
        "`/block` – reply to a sticker to block its pack\n"
        "`/blocklist` – show blocked sticker packs\n"
        "`/sticker off` – delete all stickers instantly\n"
        "`/sticker on` – allow stickers again\n"
        "`/settimer <seconds>` – auto-delete stickers after N sec\n\n"
        "**🧹 Purge** _(admin only)_\n"
        "`/purge` – delete from replied msg to now\n"
        "`/purgeall` – delete last 100 messages\n\n"
        "**📢 Broadcast** _(owner/sudo only)_\n"
        "`/broadcast <text>` – send to all groups\n\n"
        "**👑 Sudo** _(owner only)_\n"
        "`/addsudo <user>` – add sudo user\n"
        "`/rmsudo <user>` – remove sudo user\n"
        "`/sudolist` – list sudo users\n"
    )
    kb = _banner_kb(
        [InlineKeyboardButton("🗑️ Close", callback_data="close")]
    )
    await client.send_message(message.chat.id, text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
#  /config
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("config"))
async def configure(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    mode, limit, penalty = await get_config(chat_id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Warn", callback_data="warn")],
        [
            InlineKeyboardButton("🔇 Mute ✅" if penalty == "mute" else "🔇 Mute", callback_data="mute"),
            InlineKeyboardButton("🔨 Ban ✅"  if penalty == "ban"  else "🔨 Ban",  callback_data="ban"),
        ],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    await client.send_message(chat_id,
        "**⚙️ Choose penalty for users with links in bio/messages:**",
        reply_markup=kb)
    await message.delete()
    await log(client, "Config menu opened", level="CFG", chat_id=chat_id,
              extra={"by": message.from_user.id})


# ══════════════════════════════════════════════════════════════════════════════
#  WHITELIST COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("free"))
async def command_free(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(client, message)
    if not target:
        return await client.send_message(chat_id,
            "**Reply to a user or use** `/free @username`")
    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)
    kb = _banner_kb(
        [InlineKeyboardButton("🚫 Unwhitelist", callback_data=f"unwhitelist_{target.id}"),
         InlineKeyboardButton("🗑️ Close",        callback_data="close")],
    )
    await send_banner(message.chat,
        f"**✅ {target.mention} has been whitelisted.**", kb)
    await log(client, f"Whitelisted user {target.id}", level="INFO",
              chat_id=chat_id, extra={"user": target.id})


@app.on_message(filters.group & filters.command("unfree"))
async def command_unfree(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(client, message)
    if not target:
        return await client.send_message(chat_id,
            "**Reply to a user or use** `/unfree @username`")
    if await is_whitelisted(chat_id, target.id):
        await remove_whitelist(chat_id, target.id)
        txt = f"**🚫 {target.mention} removed from whitelist.**"
    else:
        txt = f"**ℹ️ {target.mention} is not whitelisted.**"
    kb = _banner_kb(
        [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target.id}"),
         InlineKeyboardButton("🗑️ Close",     callback_data="close")],
    )
    await send_banner(message.chat, txt, kb)


@app.on_message(filters.group & filters.command("freelist"))
async def command_freelist(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    ids = await get_whitelist(chat_id)
    if not ids:
        return await client.send_message(chat_id,
            "**⚠️ No whitelisted users in this group.**")
    lines = ["**📋 Whitelisted Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(f"{i}. {u.first_name} [`{uid}`]")
        except Exception:
            lines.append(f"{i}. [Unknown] [`{uid}`]")
    kb = _banner_kb([InlineKeyboardButton("🗑️ Close", callback_data="close")])
    await client.send_message(chat_id, "\n".join(lines), reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
#  WORD BLOCKLIST  (/add, /addlist)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("add"))
async def cmd_add_word(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_sudo(user_id):
        return await message.reply_text(
            "**❌ Only owner and sudo users can use this command.**")

    chat_id = message.chat.id

    # Collect word(s): from reply text OR from command argument
    words = []
    if message.reply_to_message and message.reply_to_message.text:
        words = message.reply_to_message.text.strip().split()
    elif len(message.command) > 1:
        words = message.command[1:]

    if not words:
        return await message.reply_text(
            "**Usage:** `/add <word>` or reply to a message containing the word.**")

    added = []
    for w in words:
        await add_blocked_word(chat_id, w.lower())
        added.append(w.lower())

    kb = _banner_kb(
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("➕ Add More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    )
    sent = await message.reply_text(
        f"**🚫 Word(s) added to blocklist:**\n`{'`, `'.join(added)}`",
        reply_markup=kb,
    )
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Word(s) blocked: {added}", level="ABUSE",
              chat_id=chat_id, extra={"by": user_id})


@app.on_message(filters.command("addlist"))
async def cmd_addlist(client: Client, message: Message):
    chat_id = message.chat.id
    words = await get_blocked_words(chat_id)
    if not words:
        return await message.reply_text("**📋 No blocked words in this group.**")
    text = "**🚫 Blocked Words:**\n\n" + "\n".join(f"• `{w}`" for w in words)
    kb = _banner_kb([InlineKeyboardButton("🗑️ Close", callback_data="close")])
    await message.reply_text(text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
#  STICKER CONTROLS  (/block, /blocklist, /sticker, /settimer)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("block"))
async def cmd_block_sticker(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text(
            "**Reply to a sticker to block its pack.**")
    set_name = reply.sticker.set_name
    if not set_name:
        return await message.reply_text("**This sticker has no pack.**")
    await block_sticker_set(chat_id, set_name)
    kb = _banner_kb(
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("➕ Add More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    )
    sent = await message.reply_text(
        f"**🎭 Sticker pack blocked:**\n`{set_name}`", reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Sticker pack blocked: {set_name}", level="STICK",
              chat_id=chat_id, extra={"by": message.from_user.id})


@app.on_message(filters.group & filters.command("blocklist"))
async def cmd_blocklist(client: Client, message: Message):
    chat_id = message.chat.id
    packs = await get_blocked_sticker_sets(chat_id)
    if not packs:
        return await message.reply_text("**📋 No blocked sticker packs.**")
    text = "**🎭 Blocked Sticker Packs:**\n\n" + "\n".join(
        f"{i}. `{p}`" for i, p in enumerate(packs, 1))
    kb = _banner_kb([InlineKeyboardButton("🗑️ Close", callback_data="close")])
    await message.reply_text(text, reply_markup=kb)


@app.on_message(filters.group & filters.command("sticker"))
async def cmd_sticker_toggle(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/sticker on` or `/sticker off`")
    arg = message.command[1].lower()
    if arg == "off":
        await set_sticker_mode(chat_id, False)
        kb = _banner_kb(
            [InlineKeyboardButton("🔄 Update", callback_data="noop"),
             InlineKeyboardButton("✅ Turn On", callback_data="sticker_on")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        )
        sent = await message.reply_text(
            "**🎭 Sticker mode OFF — all stickers will be deleted instantly.**",
            reply_markup=kb)
        asyncio.create_task(auto_delete(sent, 40))
        await log(client, "Sticker mode disabled", level="STICK",
                  chat_id=chat_id, extra={"by": message.from_user.id})
    elif arg == "on":
        await set_sticker_mode(chat_id, True)
        kb = _banner_kb(
            [InlineKeyboardButton("🔄 Update", callback_data="noop"),
             InlineKeyboardButton("🚫 Turn Off", callback_data="sticker_off")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        )
        sent = await message.reply_text(
            "**✅ Sticker mode ON — stickers allowed.**", reply_markup=kb)
        asyncio.create_task(auto_delete(sent, 40))
        await log(client, "Sticker mode enabled", level="STICK",
                  chat_id=chat_id, extra={"by": message.from_user.id})
    else:
        await message.reply_text("**Usage:** `/sticker on` or `/sticker off`")


@app.on_message(filters.group & filters.command("settimer"))
async def cmd_settimer(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(
            "**Usage:** `/settimer <seconds>`\nUse `0` to disable.")
    secs = int(message.command[1])
    await set_sticker_timer(chat_id, secs)
    if secs == 0:
        txt = "**⏱️ Sticker auto-delete timer disabled.**"
    else:
        txt = f"**⏱️ Stickers will auto-delete after `{secs}` seconds.**"
    kb = _banner_kb(
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",  callback_data="close")],
    )
    sent = await message.reply_text(txt, reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Sticker timer set to {secs}s", level="CFG",
              chat_id=chat_id, extra={"by": message.from_user.id})


# ══════════════════════════════════════════════════════════════════════════════
#  PURGE  (/purge, /purgeall)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("purge"))
async def cmd_purge(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    reply = message.reply_to_message
    if not reply:
        return await message.reply_text(
            "**Reply to the message from which you want to purge.**")

    start_id = reply.id
    end_id   = message.id
    ids      = list(range(start_id, end_id + 1))
    deleted  = 0

    # Delete in chunks of 100
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            await client.delete_messages(chat_id, chunk)
            deleted += len(chunk)
        except Exception:
            pass

    kb = _banner_kb(
        [InlineKeyboardButton("🧹 Purge Again", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",       callback_data="close")],
    )
    sent = await client.send_message(
        chat_id,
        f"**🧹 Purged `{deleted}` messages.**",
        reply_markup=kb,
    )
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Purge: {deleted} messages deleted", level="PURGE",
              chat_id=chat_id,
              extra={"from_msg": start_id, "to_msg": end_id, "by": message.from_user.id})


@app.on_message(filters.group & filters.command("purgeall"))
async def cmd_purgeall(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return

    deleted = 0
    ids_to_del = []
    # Collect last ~200 accessible message IDs
    async for msg in client.get_chat_history(chat_id, limit=200):
        ids_to_del.append(msg.id)

    for i in range(0, len(ids_to_del), 100):
        chunk = ids_to_del[i:i + 100]
        try:
            await client.delete_messages(chat_id, chunk)
            deleted += len(chunk)
        except Exception:
            pass

    kb = _banner_kb(
        [InlineKeyboardButton("🧹 Purge Again", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",       callback_data="close")],
    )
    sent = await client.send_message(
        chat_id,
        f"**🧹 PurgeAll complete — `{deleted}` messages deleted.**",
        reply_markup=kb,
    )
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"PurgeAll: {deleted} messages deleted", level="PURGE",
              chat_id=chat_id, extra={"by": message.from_user.id})


# ══════════════════════════════════════════════════════════════════════════════
#  BROADCAST  (/broadcast)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("broadcast"))
async def cmd_broadcast(client: Client, message: Message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text(
            "**❌ Only owner/sudo users can broadcast.**")

    text = " ".join(message.command[1:]).strip()
    if not text:
        return await message.reply_text("**Usage:** `/broadcast <message>`")

    groups  = await get_all_groups()
    success = 0
    failed  = 0
    for gid in groups:
        try:
            await client.send_message(gid, f"📢 **Broadcast:**\n\n{text}")
            success += 1
        except Exception:
            failed += 1

    await message.reply_text(
        f"**📢 Broadcast done.**\n✅ Sent: `{success}`\n❌ Failed: `{failed}`")
    await log(client, f"Broadcast sent to {success} groups", level="BROAD",
              extra={"by": message.from_user.id, "failed": failed})


# ══════════════════════════════════════════════════════════════════════════════
#  SUDO MANAGEMENT  (/addsudo, /rmsudo, /sudolist)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addsudo"))
async def cmd_addsudo(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("**❌ Only the owner can add sudo users.**")
    target = await _resolve_target(client, message)
    if not target:
        return await message.reply_text("**Reply to a user or provide username/ID.**")
    await add_sudo(target.id)
    kb = _banner_kb(
        [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
         InlineKeyboardButton("➕ Add More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    )
    sent = await message.reply_text(
        f"**👑 {target.mention} added as sudo user.**", reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Sudo added: {target.id}", level="SUDO",
              extra={"by": message.from_user.id})


@app.on_message(filters.command("rmsudo"))
async def cmd_rmsudo(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("**❌ Only the owner can remove sudo users.**")
    target = await _resolve_target(client, message)
    if not target:
        return await message.reply_text("**Reply to a user or provide username/ID.**")
    await remove_sudo(target.id)
    kb = _banner_kb(
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",  callback_data="close")],
    )
    sent = await message.reply_text(
        f"**🚫 {target.mention} removed from sudo.**", reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, f"Sudo removed: {target.id}", level="SUDO",
              extra={"by": message.from_user.id})


@app.on_message(filters.command("sudolist"))
async def cmd_sudolist(client: Client, message: Message):
    ids = await get_sudo_list()
    if not ids:
        return await message.reply_text("**👑 No sudo users configured.**")
    lines = [f"**👑 Sudo Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(f"{i}. {u.first_name} [`{uid}`]")
        except Exception:
            lines.append(f"{i}. [Unknown] [`{uid}`]")
    kb = _banner_kb([InlineKeyboardButton("🗑️ Close", callback_data="close")])
    await message.reply_text("\n".join(lines), reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK QUERIES
# ══════════════════════════════════════════════════════════════════════════════

@app.on_callback_query()
async def callback_handler(client: Client, cq):
    data    = cq.data
    chat_id = cq.message.chat.id
    user_id = cq.from_user.id

    # Generic no-op button
    if data == "noop":
        return await cq.answer()

    if data == "close":
        await cq.message.delete()
        return await cq.answer()

    # Sticker toggle via button
    if data == "sticker_off":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("❌ Admins only", show_alert=True)
        await set_sticker_mode(chat_id, False)
        await cq.answer("Sticker mode OFF ✅")
        await log(client, "Sticker mode disabled via button", level="STICK",
                  chat_id=chat_id, extra={"by": user_id})
        return

    if data == "sticker_on":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("❌ Admins only", show_alert=True)
        await set_sticker_mode(chat_id, True)
        await cq.answer("Sticker mode ON ✅")
        await log(client, "Sticker mode enabled via button", level="STICK",
                  chat_id=chat_id, extra={"by": user_id})
        return

    # Admin-only from here
    if not await is_admin(client, chat_id, user_id):
        return await cq.answer("❌ You are not an administrator.", show_alert=True)

    if data == "back":
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn", callback_data="warn")],
            [InlineKeyboardButton("🔇 Mute ✅" if penalty=="mute" else "🔇 Mute", callback_data="mute"),
             InlineKeyboardButton("🔨 Ban ✅"  if penalty=="ban"  else "🔨 Ban",  callback_data="ban")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text(
            "**⚙️ Choose penalty for users with links:**", reply_markup=kb)
        return await cq.answer()

    if data == "warn":
        _, selected_limit, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"3 ✅" if selected_limit==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"4 ✅" if selected_limit==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"5 ✅" if selected_limit==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back"),
             InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Select warn limit:**", reply_markup=kb)
        return await cq.answer()

    if data in ("mute", "ban"):
        await update_config(chat_id, penalty=data)
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn", callback_data="warn")],
            [InlineKeyboardButton("🔇 Mute ✅" if penalty=="mute" else "🔇 Mute", callback_data="mute"),
             InlineKeyboardButton("🔨 Ban ✅"  if penalty=="ban"  else "🔨 Ban",  callback_data="ban")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text("**✅ Punishment updated.**", reply_markup=kb)
        await log(client, f"Penalty set to {data}", level="CFG",
                  chat_id=chat_id, extra={"by": user_id})
        return await cq.answer()

    if data.startswith("warn_"):
        count = int(data.split("_")[1])
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"3 ✅" if count==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"4 ✅" if count==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"5 ✅" if count==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back"),
             InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text(f"**✅ Warn limit set to {count}.**", reply_markup=kb)
        await log(client, f"Warn limit set to {count}", level="CFG",
                  chat_id=chat_id, extra={"by": user_id})
        return await cq.answer()

    if data.startswith(("unmute_", "unban_")):
        action, uid = data.split("_", 1)
        target_id   = int(uid)
        try:
            if action == "unmute":
                await client.restrict_chat_member(
                    chat_id, target_id,
                    ChatPermissions(can_send_messages=True))
                verb = "unmuted"
            else:
                await client.unban_chat_member(chat_id, target_id)
                verb = "unbanned"
            await reset_warnings(chat_id, target_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target_id}"),
                 InlineKeyboardButton("🗑️ Close",    callback_data="close")],
            ])
            await cq.message.edit_text(
                f"**✅ User `{target_id}` has been {verb}.**", reply_markup=kb)
            await log(client, f"User {target_id} {verb}", level="UNMUTE" if action=="unmute" else "UNBAN",
                      chat_id=chat_id, extra={"by": user_id})
        except errors.ChatAdminRequired:
            await cq.message.edit_text("**❌ I don't have permission.**")
        return await cq.answer()

    if data.startswith("cancel_warn_"):
        target_id = int(data.split("_")[-1])
        await reset_warnings(chat_id, target_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target_id}"),
             InlineKeyboardButton("🗑️ Close",    callback_data="close")],
        ])
        await cq.message.edit_text(
            f"**✅ Warnings cleared for `{target_id}`.**", reply_markup=kb)
        return await cq.answer()

    if data.startswith("whitelist_"):
        target_id = int(data.split("_", 1)[1])
        await add_whitelist(chat_id, target_id)
        await reset_warnings(chat_id, target_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Unwhitelist", callback_data=f"unwhitelist_{target_id}"),
             InlineKeyboardButton("🗑️ Close",       callback_data="close")],
        ])
        await cq.message.edit_text(
            f"**✅ User `{target_id}` whitelisted.**", reply_markup=kb)
        return await cq.answer()

    if data.startswith("unwhitelist_"):
        target_id = int(data.split("_", 1)[1])
        await remove_whitelist(chat_id, target_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target_id}"),
             InlineKeyboardButton("🗑️ Close",    callback_data="close")],
        ])
        await cq.message.edit_text(
            f"**❌ User `{target_id}` removed from whitelist.**", reply_markup=kb)
        return await cq.answer()

    await cq.answer()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER  (bio + text link + abuse + sticker)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group)
async def guard(client: Client, message: Message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Admins and whitelisted users are exempt from all checks
    if await is_admin(client, chat_id, user_id):
        return
    if await is_whitelisted(chat_id, user_id):
        return

    user      = await client.get_chat(user_id)
    full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
    mention   = f"[{full_name}](tg://user?id={user_id})"

    # ── 1. Sticker handling ──────────────────────────────────────────────────
    if message.sticker:
        sticker_enabled = await get_sticker_mode(chat_id)
        set_name        = message.sticker.set_name or ""

        # /sticker off → delete everything immediately
        if not sticker_enabled:
            try:
                await message.delete()
            except Exception:
                pass
            kb = _banner_kb(
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("✅ Turn On Stickers", callback_data="sticker_on"),
                 InlineKeyboardButton("🗑️ Close",            callback_data="close")],
            )
            sent = await client.send_message(
                chat_id,
                f"**🎭 {mention} — stickers are disabled in this group.**",
                reply_markup=kb,
            )
            asyncio.create_task(auto_delete(sent, 40))
            await log(client, f"Sticker deleted (mode off): {user_id}",
                      level="STICK", chat_id=chat_id,
                      extra={"user": user_id, "pack": set_name})
            return

        # Blocked sticker pack
        if set_name and await is_sticker_blocked(chat_id, set_name):
            try:
                await message.delete()
            except Exception:
                pass
            kb = _banner_kb(
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            )
            sent = await client.send_message(
                chat_id,
                f"**🎭 {mention} — that sticker pack is blocked here.**",
                reply_markup=kb,
            )
            asyncio.create_task(auto_delete(sent, 40))
            await log(client, f"Blocked sticker deleted: {set_name}",
                      level="STICK", chat_id=chat_id,
                      extra={"user": user_id, "pack": set_name})
            return

        # Auto-delete timer
        timer = await get_sticker_timer(chat_id)
        if timer > 0:
            asyncio.create_task(_delayed_delete(message, timer))

        return  # sticker processed, nothing else to check

    # ── 2. Abuse / word blocklist ────────────────────────────────────────────
    msg_text = message.text or message.caption or ""
    if msg_text:
        bad_word = await is_word_blocked(chat_id, msg_text)
        if bad_word:
            try:
                await message.delete()
            except Exception:
                pass
            kb = _banner_kb(
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            )
            sent = await client.send_message(
                chat_id,
                f"**🚫 {mention} — message removed (blocked word).**",
                reply_markup=kb,
            )
            asyncio.create_task(auto_delete(sent, 40))
            await log(client, f"Blocked word detected: '{bad_word}'",
                      level="ABUSE", chat_id=chat_id,
                      extra={"user": user_id, "word": bad_word})
            return

    # ── 3. Link in message text ──────────────────────────────────────────────
    if msg_text and URL_PATTERN.search(msg_text):
        await _handle_link_violation(client, message, chat_id, user_id,
                                     mention, reason="Link in message")
        return

    # ── 4. Link in bio ───────────────────────────────────────────────────────
    bio = user.bio or ""
    if URL_PATTERN.search(bio):
        await _handle_link_violation(client, message, chat_id, user_id,
                                     mention, reason="Link in bio")
        return

    # No violation — reset any stale warnings
    await reset_warnings(chat_id, user_id)


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _delayed_delete(message: Message, seconds: int):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


async def _handle_link_violation(
    client: Client,
    message: Message,
    chat_id: int,
    user_id: int,
    mention: str,
    reason: str,
):
    """Delete message + warn/mute/ban based on config."""
    try:
        await message.delete()
    except errors.MessageDeleteForbidden:
        return await message.reply_text(
            "⚠️ Please grant me delete permission.")
    except Exception:
        pass

    mode, limit, penalty = await get_config(chat_id)

    if mode == "warn":
        count = await increment_warning(chat_id, user_id)
        warn_text = (
            f"**⚠️ Warning {count}/{limit}**\n"
            f"👤 {mention}\n"
            f"❌ Reason: {reason}"
        )
        kb = _banner_kb(
            [InlineKeyboardButton("❌ Cancel Warn",  callback_data=f"cancel_warn_{user_id}"),
             InlineKeyboardButton("✅ Whitelist",    callback_data=f"whitelist_{user_id}")],
            [InlineKeyboardButton("🗑️ Close",       callback_data="close")],
        )
        sent = await client.send_message(chat_id, warn_text, reply_markup=kb)
        asyncio.create_task(auto_delete(sent, 40))
        await log(client, f"Warned user {user_id} ({count}/{limit}): {reason}",
                  level="WARN", chat_id=chat_id,
                  extra={"user": user_id, "count": count, "limit": limit})

        if count >= limit:
            await _apply_penalty(client, chat_id, user_id, penalty, sent, mention)

    else:
        await _apply_penalty(client, chat_id, user_id, penalty, None, mention,
                             send_to=chat_id, client_ref=client)


async def _apply_penalty(
    client: Client,
    chat_id: int,
    user_id: int,
    penalty: str,
    sent_msg,
    mention: str,
    send_to: int = None,
    client_ref=None,
):
    try:
        if penalty == "mute":
            await client.restrict_chat_member(
                chat_id, user_id, ChatPermissions())
            action_text = f"**🔇 {mention} muted (Link/Abuse violation).**"
            cb_action   = f"unmute_{user_id}"
            cb_label    = "🔊 Unmute"
            log_level   = "MUTE"
        else:
            await client.ban_chat_member(chat_id, user_id)
            action_text = f"**🔨 {mention} banned (Link/Abuse violation).**"
            cb_action   = f"unban_{user_id}"
            cb_label    = "✅ Unban"
            log_level   = "BAN"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(cb_label, callback_data=cb_action),
             InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        if sent_msg:
            await sent_msg.edit_text(action_text, reply_markup=kb)
        else:
            msg = await client.send_message(chat_id, action_text, reply_markup=kb)
            asyncio.create_task(auto_delete(msg, 40))

        await log(client, f"User {user_id} {penalty}d: link/abuse",
                  level=log_level, chat_id=chat_id,
                  extra={"user": user_id, "penalty": penalty})

    except errors.ChatAdminRequired:
        txt = f"**❌ I don't have permission to {penalty} users.**"
        if sent_msg:
            await sent_msg.edit_text(txt)
        else:
            await client.send_message(chat_id, txt)


async def _resolve_target(client: Client, message: Message):
    """Return a User object from reply or command argument."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        arg = message.command[1]
        try:
            return await client.get_users(int(arg) if arg.isdigit() else arg)
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════════════════════

async def on_start():
    """Called once after app.start() — log the startup event."""
    bot = await app.get_me()
    await log(app,
              f"@{bot.username} is now online.",
              level="START",
              extra={"id": bot.id, "log_chat": str(LOG_CHAT_ID)})


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run(on_start())
