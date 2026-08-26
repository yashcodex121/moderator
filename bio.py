"""
BioLink Protector Bot  —  Enhanced Edition
Author  : Bisnu Ray  |  https://t.me/BisnuRay
Channel : https://t.me/itsSmartDev
"""

import asyncio

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
    add_blocked_word, get_blocked_words, is_word_blocked,
    block_sticker_set, get_blocked_sticker_sets, is_sticker_blocked,
    set_sticker_timer, get_sticker_timer,
    set_sticker_mode, get_sticker_mode,
    register_group, unregister_group, get_all_groups,
)
from helper.logger import log

# ─── Client ──────────────────────────────────────────────────────────────────
app = Client(
    "biolink_protector_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════

async def auto_delete(msg: Message, delay: int = 40):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


async def send_banner(chat_id: int, text: str, kb: InlineKeyboardMarkup):
    sent = await app.send_message(chat_id, text, reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    return sent


async def _resolve_target(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        arg = message.command[1]
        try:
            return await app.get_users(int(arg) if arg.isdigit() else arg)
        except Exception:
            pass
    return None


# ═════════════════════════════════════════════════════════════════════════════
#  GROUP TRACKING
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.new_chat_members)
async def on_bot_added(client: Client, message: Message):
    me = await client.get_me()
    for member in message.new_chat_members:
        if member.id == me.id:
            chat = message.chat
            await register_group(chat.id, chat.title or "")
            await log(client, f"Bot added to: {chat.title}",
                      level="JOIN", chat_id=chat.id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add to Group",
                                      url=f"https://t.me/{me.username}?startgroup=true")],
                [InlineKeyboardButton("🛠️ Support", url="https://t.me/itsSmartDev"),
                 InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME}")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            ])
            sent = await client.send_message(
                chat.id,
                "**🛡️ BioLink Protector activated!**\n\n"
                "Protecting this group from bio links, abusive words & blocked stickers.\n"
                "Use /help to see all commands.",
                reply_markup=kb,
            )
            asyncio.create_task(auto_delete(sent, 40))


@app.on_message(filters.left_chat_member)
async def on_bot_removed(client: Client, message: Message):
    me = await client.get_me()
    if message.left_chat_member and message.left_chat_member.id == me.id:
        await unregister_group(message.chat.id)
        await log(client, f"Bot removed from: {message.chat.title}",
                  level="LEFT", chat_id=message.chat.id)


# ═════════════════════════════════════════════════════════════════════════════
#  /start  /help
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    me = await client.get_me()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group",
                              url=f"https://t.me/{me.username}?startgroup=true")],
        [InlineKeyboardButton("🛠️ Support", url="https://t.me/itsSmartDev"),
         InlineKeyboardButton("👑 Owner",   url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    await message.reply_text(
        "**✨ BioLink Protector Bot ✨**\n\n"
        "🛡️ Protecting groups from bio links, abusive words & more.\n\n"
        "**Features:**\n"
        "• Bio & message link detection\n"
        "• Word / abuse blocklist\n"
        "• Sticker blocklist & timer\n"
        "• Purge, broadcast, sudo system\n\n"
        "Use /help for all commands.",
        reply_markup=kb,
    )


@app.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Close", callback_data="close")]
    ])
    await message.reply_text(
        "**🛠️ All Commands**\n\n"
        "**🔗 Bio/Link Protection**\n"
        "`/config` – warn limit & punishment\n"
        "`/free` – whitelist a user\n"
        "`/unfree` – remove from whitelist\n"
        "`/freelist` – show whitelisted users\n\n"
        "**🚫 Word Blocklist** _(owner/sudo)_\n"
        "`/add <word>` or reply to message\n"
        "`/addlist` – show blocked words\n\n"
        "**🎭 Sticker Controls** _(admin)_\n"
        "`/block` – reply to sticker to block pack\n"
        "`/blocklist` – show blocked packs\n"
        "`/sticker off|on` – disable/enable stickers\n"
        "`/settimer <sec>` – auto-delete stickers\n\n"
        "**🧹 Purge** _(admin)_\n"
        "`/purge` – delete from replied msg to now\n"
        "`/purgeall` – delete last 200 messages\n\n"
        "**📢 Broadcast** _(owner/sudo)_\n"
        "`/broadcast <text>`\n\n"
        "**👑 Sudo** _(owner only)_\n"
        "`/addsudo` `/rmsudo` `/sudolist`",
        reply_markup=kb,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  /config
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("config"))
async def configure(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    _, __, penalty = await get_config(chat_id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Warn Limit", callback_data="warn")],
        [InlineKeyboardButton("🔇 Mute ✅" if penalty == "mute" else "🔇 Mute", callback_data="mute"),
         InlineKeyboardButton("🔨 Ban ✅"  if penalty == "ban"  else "🔨 Ban",  callback_data="ban")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    sent = await client.send_message(chat_id,
        "**⚙️ Choose penalty for link violators:**", reply_markup=kb)
    await message.delete()
    asyncio.create_task(auto_delete(sent, 40))
    await log(client, "Config opened", level="CFG", chat_id=chat_id,
              extra={"by": message.from_user.id})


# ═════════════════════════════════════════════════════════════════════════════
#  WHITELIST
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("free"))
async def cmd_free(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("**Reply to a user or use `/free @username`**")
    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Unwhitelist", callback_data=f"unwhitelist_{target.id}"),
         InlineKeyboardButton("🗑️ Close",        callback_data="close")],
    ])
    await send_banner(chat_id, f"**✅ {target.mention} whitelisted.**", kb)
    await log(client, f"Whitelisted {target.id}", level="INFO", chat_id=chat_id)


@app.on_message(filters.group & filters.command("unfree"))
async def cmd_unfree(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("**Reply to a user or use `/unfree @username`**")
    await remove_whitelist(chat_id, target.id) if await is_whitelisted(chat_id, target.id) else None
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target.id}"),
         InlineKeyboardButton("🗑️ Close",     callback_data="close")],
    ])
    await send_banner(chat_id, f"**🚫 {target.mention} removed from whitelist.**", kb)


@app.on_message(filters.group & filters.command("freelist"))
async def cmd_freelist(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    ids = await get_whitelist(chat_id)
    if not ids:
        return await message.reply_text("**⚠️ No whitelisted users.**")
    lines = ["**📋 Whitelisted Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(f"{i}. {u.first_name} [`{uid}`]")
        except Exception:
            lines.append(f"{i}. Unknown [`{uid}`]")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await message.reply_text("\n".join(lines), reply_markup=kb)


# ═════════════════════════════════════════════════════════════════════════════
#  WORD BLOCKLIST
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("add"))
async def cmd_add_word(client: Client, message: Message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("**❌ Only owner/sudo can use this.**")
    chat_id = message.chat.id
    words = []
    if message.reply_to_message and message.reply_to_message.text:
        words = message.reply_to_message.text.strip().split()
    elif len(message.command) > 1:
        words = message.command[1:]
    if not words:
        return await message.reply_text("**Usage:** `/add <word>` or reply to a message.**")
    for w in words:
        await add_blocked_word(chat_id, w.lower())
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("➕ Add More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    await send_banner(chat_id,
        f"**🚫 Blocked:** `{'`, `'.join(w.lower() for w in words)}`", kb)
    await log(client, f"Words blocked: {words}", level="ABUSE", chat_id=chat_id,
              extra={"by": message.from_user.id})


@app.on_message(filters.command("addlist"))
async def cmd_addlist(client: Client, message: Message):
    chat_id = message.chat.id
    words = await get_blocked_words(chat_id)
    if not words:
        return await message.reply_text("**📋 No blocked words.**")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await message.reply_text(
        "**🚫 Blocked Words:**\n\n" + "\n".join(f"• `{w}`" for w in words),
        reply_markup=kb)


# ═════════════════════════════════════════════════════════════════════════════
#  STICKER CONTROLS
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("block"))
async def cmd_block_sticker(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text("**Reply to a sticker to block its pack.**")
    set_name = reply.sticker.set_name
    if not set_name:
        return await message.reply_text("**This sticker has no pack.**")
    await block_sticker_set(chat_id, set_name)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("➕ Block More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    await send_banner(chat_id, f"**🎭 Sticker pack blocked:** `{set_name}`", kb)
    await log(client, f"Sticker pack blocked: {set_name}", level="STICK",
              chat_id=chat_id, extra={"by": message.from_user.id})


@app.on_message(filters.group & filters.command("blocklist"))
async def cmd_blocklist(client: Client, message: Message):
    chat_id = message.chat.id
    packs = await get_blocked_sticker_sets(chat_id)
    if not packs:
        return await message.reply_text("**📋 No blocked sticker packs.**")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await message.reply_text(
        "**🎭 Blocked Sticker Packs:**\n\n" +
        "\n".join(f"{i}. `{p}`" for i, p in enumerate(packs, 1)),
        reply_markup=kb)


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
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Update", callback_data="noop"),
             InlineKeyboardButton("✅ Turn On", callback_data="sticker_on")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await send_banner(chat_id,
            "**🎭 Sticker mode OFF — all stickers deleted instantly.**", kb)
        await log(client, "Sticker mode OFF", level="STICK", chat_id=chat_id,
                  extra={"by": message.from_user.id})
    elif arg == "on":
        await set_sticker_mode(chat_id, True)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Update", callback_data="noop"),
             InlineKeyboardButton("🚫 Turn Off", callback_data="sticker_off")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await send_banner(chat_id, "**✅ Sticker mode ON.**", kb)
        await log(client, "Sticker mode ON", level="STICK", chat_id=chat_id,
                  extra={"by": message.from_user.id})
    else:
        await message.reply_text("**Usage:** `/sticker on` or `/sticker off`")


@app.on_message(filters.group & filters.command("settimer"))
async def cmd_settimer(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("**Usage:** `/settimer <seconds>` (0 = off)")
    secs = int(message.command[1])
    await set_sticker_timer(chat_id, secs)
    txt = ("**⏱️ Sticker auto-delete timer disabled.**" if secs == 0
           else f"**⏱️ Stickers auto-delete after `{secs}` seconds.**")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",  callback_data="close")],
    ])
    await send_banner(chat_id, txt, kb)
    await log(client, f"Sticker timer set to {secs}s", level="CFG",
              chat_id=chat_id, extra={"by": message.from_user.id})


# ═════════════════════════════════════════════════════════════════════════════
#  PURGE
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group & filters.command("purge"))
async def cmd_purge(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if not message.reply_to_message:
        return await message.reply_text("**Reply to a message to start purge from.**")
    ids = list(range(message.reply_to_message.id, message.id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        try:
            await client.delete_messages(chat_id, ids[i:i+100])
            deleted += len(ids[i:i+100])
        except Exception:
            pass
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Purge Again", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",       callback_data="close")],
    ])
    await send_banner(chat_id, f"**🧹 Purged `{deleted}` messages.**", kb)
    await log(client, f"Purge: {deleted} msgs deleted", level="PURGE",
              chat_id=chat_id, extra={"by": message.from_user.id})


@app.on_message(filters.group & filters.command("purgeall"))
async def cmd_purgeall(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    ids = []
    async for msg in client.get_chat_history(chat_id, limit=200):
        ids.append(msg.id)
    deleted = 0
    for i in range(0, len(ids), 100):
        try:
            await client.delete_messages(chat_id, ids[i:i+100])
            deleted += len(ids[i:i+100])
        except Exception:
            pass
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Purge Again", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",       callback_data="close")],
    ])
    await send_banner(chat_id, f"**🧹 PurgeAll: `{deleted}` messages deleted.**", kb)
    await log(client, f"PurgeAll: {deleted} msgs", level="PURGE",
              chat_id=chat_id, extra={"by": message.from_user.id})


# ═════════════════════════════════════════════════════════════════════════════
#  BROADCAST
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("broadcast"))
async def cmd_broadcast(client: Client, message: Message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("**❌ Only owner/sudo can broadcast.**")
    text = " ".join(message.command[1:]).strip()
    if not text:
        return await message.reply_text("**Usage:** `/broadcast <message>`")
    groups = await get_all_groups()
    ok = fail = 0
    for gid in groups:
        try:
            await client.send_message(gid, f"📢 **Broadcast:**\n\n{text}")
            ok += 1
        except Exception:
            fail += 1
    await message.reply_text(f"**📢 Broadcast done.**\n✅ Sent: `{ok}`\n❌ Failed: `{fail}`")
    await log(client, f"Broadcast to {ok} groups", level="BROAD",
              extra={"by": message.from_user.id, "failed": fail})


# ═════════════════════════════════════════════════════════════════════════════
#  SUDO MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("addsudo"))
async def cmd_addsudo(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("**❌ Only owner can add sudo.**")
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("**Reply to a user or provide username/ID.**")
    await add_sudo(target.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
         InlineKeyboardButton("➕ Add More", callback_data="noop")],
        [InlineKeyboardButton("🗑️ Close", callback_data="close")],
    ])
    await send_banner(message.chat.id,
        f"**👑 {target.mention} added as sudo.**", kb)
    await log(client, f"Sudo added: {target.id}", level="SUDO",
              extra={"by": message.from_user.id})


@app.on_message(filters.command("rmsudo"))
async def cmd_rmsudo(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("**❌ Only owner can remove sudo.**")
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("**Reply to a user or provide username/ID.**")
    await remove_sudo(target.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update", callback_data="noop"),
         InlineKeyboardButton("🗑️ Close",  callback_data="close")],
    ])
    await send_banner(message.chat.id,
        f"**🚫 {target.mention} removed from sudo.**", kb)
    await log(client, f"Sudo removed: {target.id}", level="SUDO",
              extra={"by": message.from_user.id})


@app.on_message(filters.command("sudolist"))
async def cmd_sudolist(client: Client, message: Message):
    ids = await get_sudo_list()
    if not ids:
        return await message.reply_text("**👑 No sudo users.**")
    lines = ["**👑 Sudo Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(f"{i}. {u.first_name} [`{uid}`]")
        except Exception:
            lines.append(f"{i}. Unknown [`{uid}`]")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await message.reply_text("\n".join(lines), reply_markup=kb)


# ═════════════════════════════════════════════════════════════════════════════
#  CALLBACK QUERIES
# ═════════════════════════════════════════════════════════════════════════════

@app.on_callback_query()
async def callback_handler(client: Client, cq):
    data    = cq.data
    chat_id = cq.message.chat.id
    user_id = cq.from_user.id

    if data == "noop":
        return await cq.answer()

    if data == "close":
        await cq.message.delete()
        return await cq.answer()

    if data == "sticker_off":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("❌ Admins only", show_alert=True)
        await set_sticker_mode(chat_id, False)
        await cq.answer("Sticker mode OFF ✅")
        return

    if data == "sticker_on":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("❌ Admins only", show_alert=True)
        await set_sticker_mode(chat_id, True)
        await cq.answer("Sticker mode ON ✅")
        return

    if not await is_admin(client, chat_id, user_id):
        return await cq.answer("❌ Not an admin.", show_alert=True)

    if data == "back":
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn Limit", callback_data="warn")],
            [InlineKeyboardButton("🔇 Mute ✅" if penalty=="mute" else "🔇 Mute", callback_data="mute"),
             InlineKeyboardButton("🔨 Ban ✅"  if penalty=="ban"  else "🔨 Ban",  callback_data="ban")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text("**⚙️ Choose penalty:**", reply_markup=kb)
        return await cq.answer()

    if data == "warn":
        _, lim, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"3 ✅" if lim==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"4 ✅" if lim==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"5 ✅" if lim==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back"),
             InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Select warn limit:**", reply_markup=kb)
        return await cq.answer()

    if data in ("mute", "ban"):
        await update_config(chat_id, penalty=data)
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn Limit", callback_data="warn")],
            [InlineKeyboardButton("🔇 Mute ✅" if penalty=="mute" else "🔇 Mute", callback_data="mute"),
             InlineKeyboardButton("🔨 Ban ✅"  if penalty=="ban"  else "🔨 Ban",  callback_data="ban")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        await cq.message.edit_text("**✅ Punishment updated.**", reply_markup=kb)
        await log(client, f"Penalty → {data}", level="CFG",
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
        await cq.message.edit_text(f"**✅ Warn limit → {count}**", reply_markup=kb)
        return await cq.answer()

    if data.startswith(("unmute_", "unban_")):
        action, uid = data.split("_", 1)
        target_id = int(uid)
        try:
            if action == "unmute":
                await client.restrict_chat_member(
                    chat_id, target_id, ChatPermissions(can_send_messages=True))
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
                f"**✅ User `{target_id}` {verb}.**", reply_markup=kb)
        except errors.ChatAdminRequired:
            await cq.message.edit_text("**❌ No permission.**")
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
            f"**✅ `{target_id}` whitelisted.**", reply_markup=kb)
        return await cq.answer()

    if data.startswith("unwhitelist_"):
        target_id = int(data.split("_", 1)[1])
        await remove_whitelist(chat_id, target_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{target_id}"),
             InlineKeyboardButton("🗑️ Close",    callback_data="close")],
        ])
        await cq.message.edit_text(
            f"**❌ `{target_id}` removed from whitelist.**", reply_markup=kb)
        return await cq.answer()

    await cq.answer()


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN GUARD  (bio link + message link + abuse + sticker)
# ═════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.group)
async def guard(client: Client, message: Message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(client, chat_id, user_id):
        return
    if await is_whitelisted(chat_id, user_id):
        return

    user      = await client.get_chat(user_id)
    full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
    mention   = f"[{full_name}](tg://user?id={user_id})"

    # ── Sticker ──────────────────────────────────────────────────────────────
    if message.sticker:
        sticker_on = await get_sticker_mode(chat_id)
        set_name   = message.sticker.set_name or ""

        if not sticker_on:
            try:
                await message.delete()
            except Exception:
                pass
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("✅ Enable Stickers", callback_data="sticker_on"),
                 InlineKeyboardButton("🗑️ Close",            callback_data="close")],
            ])
            await send_banner(chat_id,
                f"**🎭 {mention} — stickers are disabled here.**", kb)
            await log(client, f"Sticker deleted (mode off): {user_id}",
                      level="STICK", chat_id=chat_id)
            return

        if set_name and await is_sticker_blocked(chat_id, set_name):
            try:
                await message.delete()
            except Exception:
                pass
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            ])
            await send_banner(chat_id,
                f"**🎭 {mention} — that sticker pack is blocked.**", kb)
            await log(client, f"Blocked sticker deleted: {set_name}",
                      level="STICK", chat_id=chat_id, extra={"user": user_id})
            return

        timer = await get_sticker_timer(chat_id)
        if timer > 0:
            asyncio.create_task(_delayed_delete(message, timer))
        return

    # ── Abuse / word blocklist ────────────────────────────────────────────────
    msg_text = message.text or message.caption or ""
    if msg_text:
        bad_word = await is_word_blocked(chat_id, msg_text)
        if bad_word:
            try:
                await message.delete()
            except Exception:
                pass
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Update",   callback_data="noop"),
                 InlineKeyboardButton("➕ Add More", callback_data="noop")],
                [InlineKeyboardButton("🗑️ Close", callback_data="close")],
            ])
            await send_banner(chat_id,
                f"**🚫 {mention} — message removed (blocked word).**", kb)
            await log(client, f"Blocked word '{bad_word}' caught",
                      level="ABUSE", chat_id=chat_id,
                      extra={"user": user_id, "word": bad_word})
            return

    # ── Link in message ───────────────────────────────────────────────────────
    if msg_text and URL_PATTERN.search(msg_text):
        await _handle_link_violation(client, message, chat_id, user_id,
                                     mention, "Link in message")
        return

    # ── Link in bio ───────────────────────────────────────────────────────────
    bio = user.bio or ""
    if URL_PATTERN.search(bio):
        await _handle_link_violation(client, message, chat_id, user_id,
                                     mention, "Link in bio")
        return

    await reset_warnings(chat_id, user_id)


# ═════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

async def _delayed_delete(message: Message, seconds: int):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


async def _handle_link_violation(client, message, chat_id, user_id, mention, reason):
    try:
        await message.delete()
    except errors.MessageDeleteForbidden:
        return await message.reply_text("⚠️ Please grant me delete permission.")
    except Exception:
        pass

    mode, limit, penalty = await get_config(chat_id)

    if mode == "warn":
        count = await increment_warning(chat_id, user_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Warn", callback_data=f"cancel_warn_{user_id}"),
             InlineKeyboardButton("✅ Whitelist",   callback_data=f"whitelist_{user_id}")],
            [InlineKeyboardButton("🗑️ Close",      callback_data="close")],
        ])
        sent = await client.send_message(
            chat_id,
            f"**⚠️ Warning {count}/{limit}**\n"
            f"👤 {mention}\n"
            f"❌ Reason: {reason}",
            reply_markup=kb,
        )
        asyncio.create_task(auto_delete(sent, 40))
        await log(client, f"Warned {user_id} ({count}/{limit}): {reason}",
                  level="WARN", chat_id=chat_id,
                  extra={"user": user_id, "count": count})

        if count >= limit:
            await _apply_penalty(client, chat_id, user_id, penalty, sent, mention)
    else:
        await _apply_penalty(client, chat_id, user_id, penalty, None, mention,
                             send_to=chat_id)


async def _apply_penalty(client, chat_id, user_id, penalty,
                          sent_msg, mention, send_to=None):
    try:
        if penalty == "mute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            txt      = f"**🔇 {mention} muted (link/abuse violation).**"
            cb_data  = f"unmute_{user_id}"
            cb_label = "🔊 Unmute"
            lvl      = "MUTE"
        else:
            await client.ban_chat_member(chat_id, user_id)
            txt      = f"**🔨 {mention} banned (link/abuse violation).**"
            cb_data  = f"unban_{user_id}"
            cb_label = "✅ Unban"
            lvl      = "BAN"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(cb_label,   callback_data=cb_data),
             InlineKeyboardButton("🗑️ Close", callback_data="close")],
        ])
        if sent_msg:
            await sent_msg.edit_text(txt, reply_markup=kb)
        else:
            msg = await client.send_message(send_to or chat_id, txt, reply_markup=kb)
            asyncio.create_task(auto_delete(msg, 40))

        await log(client, f"User {user_id} {penalty}d", level=lvl,
                  chat_id=chat_id, extra={"user": user_id})

    except errors.ChatAdminRequired:
        err = f"**❌ No permission to {penalty}.**"
        if sent_msg:
            await sent_msg.edit_text(err)
        else:
            await client.send_message(send_to or chat_id, err)


# ═════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ═════════════════════════════════════════════════════════════════════════════

async def _post_start():
    bot = await app.get_me()
    await log(app, f"@{bot.username} is now online.",
              level="START",
              extra={"id": bot.id, "log_chat": str(LOG_CHAT_ID)})


if __name__ == "__main__":
    app.run(_post_start())
