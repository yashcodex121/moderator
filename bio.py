"""
BioLink Protector Bot  —  Enhanced Edition
Author  : Bisnu Ray  |  https://t.me/BisnuRay
"""

import asyncio

from pyrogram import Client, filters, errors
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, Message,
)
from config import (
    API_ID, API_HASH, BOT_TOKEN, OWNER_ID, OWNER_USERNAME, LOG_CHAT_ID, URL_PATTERN,
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

app = Client("biolink_protector_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def auto_delete(msg, delay=40):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


async def send_banner(chat_id, text, kb):
    sent = await app.send_message(chat_id, text, reply_markup=kb)
    asyncio.create_task(auto_delete(sent, 40))
    return sent


async def _resolve_target(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        arg = message.command[1]
        try:
            return await app.get_users(int(arg) if arg.isdigit() else arg)
        except Exception:
            pass
    return None


# ── Group tracking ────────────────────────────────────────────────────────────

@app.on_message(filters.new_chat_members)
async def on_bot_added(client, message):
    me = await client.get_me()
    for member in message.new_chat_members:
        if member.id == me.id:
            chat = message.chat
            await register_group(chat.id, chat.title or "")
            await log(client, "Bot added to: " + str(chat.title), level="JOIN", chat_id=chat.id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Add to Group", url="https://t.me/" + me.username + "?startgroup=true")],
                [InlineKeyboardButton("Support", url="https://t.me/itsSmartDev"),
                 InlineKeyboardButton("Owner", url="https://t.me/" + OWNER_USERNAME)],
                [InlineKeyboardButton("Close", callback_data="close")],
            ])
            sent = await client.send_message(chat.id,
                "**BioLink Protector activated!**\n\nProtecting this group from bio links, abusive words & blocked stickers.\nUse /help to see all commands.",
                reply_markup=kb)
            asyncio.create_task(auto_delete(sent, 40))


@app.on_message(filters.left_chat_member)
async def on_bot_removed(client, message):
    me = await client.get_me()
    if message.left_chat_member and message.left_chat_member.id == me.id:
        await unregister_group(message.chat.id)
        await log(client, "Bot removed from: " + str(message.chat.title), level="LEFT", chat_id=message.chat.id)


# ── /start /help ──────────────────────────────────────────────────────────────

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    me = await client.get_me()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Add to Group", url="https://t.me/" + me.username + "?startgroup=true")],
        [InlineKeyboardButton("Support", url="https://t.me/itsSmartDev"),
         InlineKeyboardButton("Owner", url="https://t.me/" + OWNER_USERNAME)],
        [InlineKeyboardButton("Close", callback_data="close")],
    ])
    await message.reply_text(
        "**BioLink Protector Bot**\n\nProtecting groups from bio links, abusive words & more.\n\nFeatures:\n- Bio & message link detection\n- Word/abuse blocklist\n- Sticker blocklist & timer\n- Purge, broadcast, sudo system\n\nUse /help for all commands.",
        reply_markup=kb)


@app.on_message(filters.command("help"))
async def help_handler(client, message):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]])
    await message.reply_text(
        "**All Commands**\n\n**Bio/Link Protection**\n/config - warn limit & punishment\n/free - whitelist user\n/unfree - remove whitelist\n/freelist - show whitelist\n\n**Word Blocklist** (owner/sudo)\n/add word\n/addlist\n\n**Sticker Controls** (admin)\n/block - reply to sticker\n/blocklist\n/sticker off or on\n/settimer seconds\n\n**Purge** (admin)\n/purge - from replied msg\n/purgeall - last 200 msgs\n\n**Broadcast** (owner/sudo)\n/broadcast message\n\n**Sudo** (owner only)\n/addsudo /rmsudo /sudolist",
        reply_markup=kb)


# ── /config ───────────────────────────────────────────────────────────────────

@app.on_message(filters.group & filters.command("config"))
async def configure(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    _, __, penalty = await get_config(chat_id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Warn Limit", callback_data="warn")],
        [InlineKeyboardButton("Mute ✅" if penalty == "mute" else "Mute", callback_data="mute"),
         InlineKeyboardButton("Ban ✅" if penalty == "ban" else "Ban", callback_data="ban")],
        [InlineKeyboardButton("Close", callback_data="close")],
    ])
    sent = await client.send_message(chat_id, "**Choose penalty for link violators:**", reply_markup=kb)
    await message.delete()
    asyncio.create_task(auto_delete(sent, 40))


# ── Whitelist ─────────────────────────────────────────────────────────────────

@app.on_message(filters.group & filters.command("free"))
async def cmd_free(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("Reply to a user or use /free @username")
    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Unwhitelist", callback_data="unwhitelist_" + str(target.id)),
         InlineKeyboardButton("Close", callback_data="close")],
    ])
    await send_banner(chat_id, "**" + target.mention + " whitelisted.**", kb)


@app.on_message(filters.group & filters.command("unfree"))
async def cmd_unfree(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("Reply to a user or use /unfree @username")
    if await is_whitelisted(chat_id, target.id):
        await remove_whitelist(chat_id, target.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Whitelist", callback_data="whitelist_" + str(target.id)),
         InlineKeyboardButton("Close", callback_data="close")],
    ])
    await send_banner(chat_id, "**" + target.mention + " removed from whitelist.**", kb)


@app.on_message(filters.group & filters.command("freelist"))
async def cmd_freelist(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    ids = await get_whitelist(chat_id)
    if not ids:
        return await message.reply_text("No whitelisted users.")
    lines = ["**Whitelisted Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(str(i) + ". " + u.first_name + " [" + str(uid) + "]")
        except Exception:
            lines.append(str(i) + ". Unknown [" + str(uid) + "]")
    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


# ── Word blocklist ────────────────────────────────────────────────────────────

@app.on_message(filters.command("add"))
async def cmd_add_word(client, message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("Only owner/sudo can use this.")
    chat_id = message.chat.id
    words = []
    if message.reply_to_message and message.reply_to_message.text:
        words = message.reply_to_message.text.strip().split()
    elif len(message.command) > 1:
        words = message.command[1:]
    if not words:
        return await message.reply_text("Usage: /add word or reply to a message.")
    for w in words:
        await add_blocked_word(chat_id, w.lower())
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Update", callback_data="noop"),
         InlineKeyboardButton("Add More", callback_data="noop")],
        [InlineKeyboardButton("Close", callback_data="close")],
    ])
    await send_banner(chat_id, "**Blocked:** " + ", ".join(w.lower() for w in words), kb)


@app.on_message(filters.command("addlist"))
async def cmd_addlist(client, message):
    words = await get_blocked_words(message.chat.id)
    if not words:
        return await message.reply_text("No blocked words.")
    await message.reply_text("**Blocked Words:**\n\n" + "\n".join("- " + w for w in words),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


# ── Sticker controls ──────────────────────────────────────────────────────────

@app.on_message(filters.group & filters.command("block"))
async def cmd_block_sticker(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text("Reply to a sticker to block its pack.")
    set_name = reply.sticker.set_name
    if not set_name:
        return await message.reply_text("This sticker has no pack.")
    await block_sticker_set(chat_id, set_name)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Update", callback_data="noop"),
         InlineKeyboardButton("Block More", callback_data="noop")],
        [InlineKeyboardButton("Close", callback_data="close")],
    ])
    await send_banner(chat_id, "**Sticker pack blocked:** " + set_name, kb)


@app.on_message(filters.group & filters.command("blocklist"))
async def cmd_blocklist(client, message):
    packs = await get_blocked_sticker_sets(message.chat.id)
    if not packs:
        return await message.reply_text("No blocked sticker packs.")
    await message.reply_text("**Blocked Sticker Packs:**\n\n" + "\n".join(str(i) + ". " + p for i, p in enumerate(packs, 1)),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


@app.on_message(filters.group & filters.command("sticker"))
async def cmd_sticker_toggle(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if len(message.command) < 2:
        return await message.reply_text("Usage: /sticker on or /sticker off")
    arg = message.command[1].lower()
    if arg == "off":
        await set_sticker_mode(chat_id, False)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Update", callback_data="noop"),
             InlineKeyboardButton("Turn On", callback_data="sticker_on")],
            [InlineKeyboardButton("Close", callback_data="close")],
        ])
        await send_banner(chat_id, "**Sticker mode OFF — all stickers deleted instantly.**", kb)
        await log(client, "Sticker mode OFF", level="STICK", chat_id=chat_id)
    elif arg == "on":
        await set_sticker_mode(chat_id, True)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Update", callback_data="noop"),
             InlineKeyboardButton("Turn Off", callback_data="sticker_off")],
            [InlineKeyboardButton("Close", callback_data="close")],
        ])
        await send_banner(chat_id, "**Sticker mode ON.**", kb)
        await log(client, "Sticker mode ON", level="STICK", chat_id=chat_id)
    else:
        await message.reply_text("Usage: /sticker on or /sticker off")


@app.on_message(filters.group & filters.command("settimer"))
async def cmd_settimer(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: /settimer seconds (0 = off)")
    secs = int(message.command[1])
    await set_sticker_timer(chat_id, secs)
    txt = "**Timer disabled.**" if secs == 0 else "**Stickers auto-delete after " + str(secs) + " seconds.**"
    await send_banner(chat_id, txt, InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


# ── Purge ─────────────────────────────────────────────────────────────────────

@app.on_message(filters.group & filters.command("purge"))
async def cmd_purge(client, message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        return
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to start purge from.")
    ids = list(range(message.reply_to_message.id, message.id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        try:
            await client.delete_messages(chat_id, ids[i:i+100])
            deleted += len(ids[i:i+100])
        except Exception:
            pass
    await send_banner(chat_id, "**Purged " + str(deleted) + " messages.**",
        InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))
    await log(client, "Purge: " + str(deleted) + " msgs", level="PURGE", chat_id=chat_id)


@app.on_message(filters.group & filters.command("purgeall"))
async def cmd_purgeall(client, message):
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
    await send_banner(chat_id, "**PurgeAll: " + str(deleted) + " messages deleted.**",
        InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))
    await log(client, "PurgeAll: " + str(deleted) + " msgs", level="PURGE", chat_id=chat_id)


# ── Broadcast ─────────────────────────────────────────────────────────────────

@app.on_message(filters.command("broadcast"))
async def cmd_broadcast(client, message):
    if not await is_sudo(message.from_user.id):
        return await message.reply_text("Only owner/sudo can broadcast.")
    text = " ".join(message.command[1:]).strip()
    if not text:
        return await message.reply_text("Usage: /broadcast message")
    try:
        await register_group(message.chat.id, message.chat.title or "")
    except Exception:
        pass
    groups = await get_all_groups()
    if not groups:
        return await message.reply_text("No groups registered yet.")
    ok = fail = 0
    status_msg = await message.reply_text("Broadcasting to " + str(len(groups)) + " groups...")
    for gid in groups:
        try:
            await client.send_message(gid, "Broadcast:\n\n" + text, parse_mode=None)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.3)
    await status_msg.edit_text("Broadcast done.\nSent: " + str(ok) + "\nFailed: " + str(fail))


# ── Sudo ──────────────────────────────────────────────────────────────────────

@app.on_message(filters.command("addsudo"))
async def cmd_addsudo(client, message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("Only owner can add sudo.")
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("Reply to a user or provide username/ID.")
    await add_sudo(target.id)
    await send_banner(message.chat.id, "**" + target.mention + " added as sudo.**",
        InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


@app.on_message(filters.command("rmsudo"))
async def cmd_rmsudo(client, message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("Only owner can remove sudo.")
    target = await _resolve_target(message)
    if not target:
        return await message.reply_text("Reply to a user or provide username/ID.")
    await remove_sudo(target.id)
    await send_banner(message.chat.id, "**" + target.mention + " removed from sudo.**",
        InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


@app.on_message(filters.command("sudolist"))
async def cmd_sudolist(client, message):
    ids = await get_sudo_list()
    if not ids:
        return await message.reply_text("No sudo users.")
    lines = ["**Sudo Users:**\n"]
    for i, uid in enumerate(ids, 1):
        try:
            u = await client.get_users(uid)
            lines.append(str(i) + ". " + u.first_name + " [" + str(uid) + "]")
        except Exception:
            lines.append(str(i) + ". Unknown [" + str(uid) + "]")
    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.on_callback_query()
async def callback_handler(client, cq):
    data = cq.data
    chat_id = cq.message.chat.id
    user_id = cq.from_user.id
    if data == "noop":
        return await cq.answer()
    if data == "close":
        await cq.message.delete()
        return await cq.answer()
    if data == "sticker_off":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("Admins only", show_alert=True)
        await set_sticker_mode(chat_id, False)
        return await cq.answer("Sticker mode OFF")
    if data == "sticker_on":
        if not await is_admin(client, chat_id, user_id):
            return await cq.answer("Admins only", show_alert=True)
        await set_sticker_mode(chat_id, True)
        return await cq.answer("Sticker mode ON")
    if not await is_admin(client, chat_id, user_id):
        return await cq.answer("Not an admin.", show_alert=True)
    if data == "back":
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn Limit", callback_data="warn")],
            [InlineKeyboardButton("Mute ✅" if penalty == "mute" else "Mute", callback_data="mute"),
             InlineKeyboardButton("Ban ✅" if penalty == "ban" else "Ban", callback_data="ban")],
            [InlineKeyboardButton("Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Choose penalty:**", reply_markup=kb)
        return await cq.answer()
    if data == "warn":
        _, lim, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("3 ✅" if lim == 3 else "3", callback_data="warn_3"),
             InlineKeyboardButton("4 ✅" if lim == 4 else "4", callback_data="warn_4"),
             InlineKeyboardButton("5 ✅" if lim == 5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"),
             InlineKeyboardButton("Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Select warn limit:**", reply_markup=kb)
        return await cq.answer()
    if data in ("mute", "ban"):
        await update_config(chat_id, penalty=data)
        _, __, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn Limit", callback_data="warn")],
            [InlineKeyboardButton("Mute ✅" if penalty == "mute" else "Mute", callback_data="mute"),
             InlineKeyboardButton("Ban ✅" if penalty == "ban" else "Ban", callback_data="ban")],
            [InlineKeyboardButton("Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Punishment updated.**", reply_markup=kb)
        return await cq.answer()
    if data.startswith("warn_"):
        count = int(data.split("_")[1])
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("3 ✅" if count == 3 else "3", callback_data="warn_3"),
             InlineKeyboardButton("4 ✅" if count == 4 else "4", callback_data="warn_4"),
             InlineKeyboardButton("5 ✅" if count == 5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"),
             InlineKeyboardButton("Close", callback_data="close")],
        ])
        await cq.message.edit_text("**Warn limit set to " + str(count) + ".**", reply_markup=kb)
        return await cq.answer()
    if data.startswith(("unmute_", "unban_")):
        action, uid = data.split("_", 1)
        target_id = int(uid)
        try:
            if action == "unmute":
                await client.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=True))
                verb = "unmuted"
            else:
                await client.unban_chat_member(chat_id, target_id)
                verb = "unbanned"
            await reset_warnings(chat_id, target_id)
            await cq.message.edit_text("**User " + str(target_id) + " " + verb + ".**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Whitelist", callback_data="whitelist_" + str(target_id)),
                    InlineKeyboardButton("Close", callback_data="close")]]))
        except errors.ChatAdminRequired:
            await cq.message.edit_text("No permission.")
        return await cq.answer()
    if data.startswith("cancel_warn_"):
        target_id = int(data.split("_")[-1])
        await reset_warnings(chat_id, target_id)
        await cq.message.edit_text("**Warnings cleared for " + str(target_id) + ".**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Whitelist", callback_data="whitelist_" + str(target_id)),
                InlineKeyboardButton("Close", callback_data="close")]]))
        return await cq.answer()
    if data.startswith("whitelist_"):
        target_id = int(data.split("_", 1)[1])
        await add_whitelist(chat_id, target_id)
        await reset_warnings(chat_id, target_id)
        await cq.message.edit_text("**" + str(target_id) + " whitelisted.**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Unwhitelist", callback_data="unwhitelist_" + str(target_id)),
                InlineKeyboardButton("Close", callback_data="close")]]))
        return await cq.answer()
    if data.startswith("unwhitelist_"):
        target_id = int(data.split("_", 1)[1])
        await remove_whitelist(chat_id, target_id)
        await cq.message.edit_text("**" + str(target_id) + " removed from whitelist.**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Whitelist", callback_data="whitelist_" + str(target_id)),
                InlineKeyboardButton("Close", callback_data="close")]]))
        return await cq.answer()
    await cq.answer()


# ── Sticker handler (runs BEFORE guard, catches ALL stickers including admins) ─

@app.on_message(filters.group & filters.sticker)
async def sticker_handler(client, message):
    """
    Dedicated sticker handler — runs independently of guard.
    Handles: sticker mode off, blocked packs, auto-delete timer.
    NOTE: Even admins are affected by sticker mode off and blocked packs.
    """
    chat_id = message.chat.id
    if not message.from_user:
        return

    user_id = message.from_user.id
    set_name = message.sticker.set_name or "" if message.sticker else ""

    # ── sticker mode completely off ───────────────────────────────────────────
    sticker_on = await get_sticker_mode(chat_id)
    if not sticker_on:
        try:
            await message.delete()
        except Exception:
            pass
        user = await client.get_chat(user_id)
        full_name = user.first_name + (" " + user.last_name if user.last_name else "")
        mention = "[" + full_name + "](tg://user?id=" + str(user_id) + ")"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Enable Stickers", callback_data="sticker_on"),
             InlineKeyboardButton("Close", callback_data="close")],
        ])
        await send_banner(chat_id, mention + " — stickers are disabled here.", kb)
        await log(client, "Sticker deleted (mode off) from " + str(user_id), level="STICK", chat_id=chat_id)
        return

    # ── blocked sticker pack ──────────────────────────────────────────────────
    if set_name and await is_sticker_blocked(chat_id, set_name):
        try:
            await message.delete()
        except Exception:
            pass
        user = await client.get_chat(user_id)
        full_name = user.first_name + (" " + user.last_name if user.last_name else "")
        mention = "[" + full_name + "](tg://user?id=" + str(user_id) + ")"
        await send_banner(chat_id, mention + " — that sticker pack is blocked.",
            InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]))
        await log(client, "Blocked sticker deleted: " + set_name, level="STICK", chat_id=chat_id)
        return

    # ── auto-delete timer ─────────────────────────────────────────────────────
    timer = await get_sticker_timer(chat_id)
    if timer > 0:
        asyncio.create_task(_delayed_delete(message, timer))


# ── Main guard (text/link/abuse — excludes stickers handled above) ────────────

@app.on_message(filters.group & ~filters.sticker)
async def guard(client, message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    # admins exempt from link/abuse checks
    if await is_admin(client, chat_id, user_id):
        return
    if await is_whitelisted(chat_id, user_id):
        return

    user = await client.get_chat(user_id)
    full_name = user.first_name + (" " + user.last_name if user.last_name else "")
    mention = "[" + full_name + "](tg://user?id=" + str(user_id) + ")"

    msg_text = message.text or message.caption or ""

    # ── abuse / word blocklist ─────────────────────────────────────────────────
    if msg_text:
        bad_word = await is_word_blocked(chat_id, msg_text)
        if bad_word:
            try:
                await message.delete()
            except Exception:
                pass
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Update", callback_data="noop"),
                 InlineKeyboardButton("Add More", callback_data="noop")],
                [InlineKeyboardButton("Close", callback_data="close")],
            ])
            await send_banner(chat_id, mention + " — message removed (blocked word).", kb)
            return

    # ── link in message ────────────────────────────────────────────────────────
    if msg_text and URL_PATTERN.search(msg_text):
        await _handle_link_violation(client, message, chat_id, user_id, mention, "Link in message")
        return

    # ── link in bio ────────────────────────────────────────────────────────────
    bio = user.bio or ""
    if URL_PATTERN.search(bio):
        await _handle_link_violation(client, message, chat_id, user_id, mention, "Link in bio")
        return

    await reset_warnings(chat_id, user_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _delayed_delete(message, seconds):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


async def _handle_link_violation(client, message, chat_id, user_id, mention, reason):
    try:
        await message.delete()
    except errors.MessageDeleteForbidden:
        return await message.reply_text("Please grant me delete permission.")
    except Exception:
        pass
    mode, limit, penalty = await get_config(chat_id)
    if mode == "warn":
        count = await increment_warning(chat_id, user_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Warn", callback_data="cancel_warn_" + str(user_id)),
             InlineKeyboardButton("Whitelist", callback_data="whitelist_" + str(user_id))],
            [InlineKeyboardButton("Close", callback_data="close")],
        ])
        sent = await client.send_message(chat_id,
            "**Warning " + str(count) + "/" + str(limit) + "**\n" + mention + "\nReason: " + reason,
            reply_markup=kb)
        asyncio.create_task(auto_delete(sent, 40))
        await log(client, "Warned " + str(user_id), level="WARN", chat_id=chat_id)
        if count >= limit:
            await _apply_penalty(client, chat_id, user_id, penalty, sent, mention)
    else:
        await _apply_penalty(client, chat_id, user_id, penalty, None, mention, send_to=chat_id)


async def _apply_penalty(client, chat_id, user_id, penalty, sent_msg, mention, send_to=None):
    try:
        if penalty == "mute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            txt = mention + " muted (link/abuse violation)."
            cb_data, cb_label, lvl = "unmute_" + str(user_id), "Unmute", "MUTE"
        else:
            await client.ban_chat_member(chat_id, user_id)
            txt = mention + " banned (link/abuse violation)."
            cb_data, cb_label, lvl = "unban_" + str(user_id), "Unban", "BAN"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(cb_label, callback_data=cb_data),
             InlineKeyboardButton("Close", callback_data="close")],
        ])
        if sent_msg:
            await sent_msg.edit_text("**" + txt + "**", reply_markup=kb)
        else:
            msg = await client.send_message(send_to or chat_id, "**" + txt + "**", reply_markup=kb)
            asyncio.create_task(auto_delete(msg, 40))
        await log(client, "User " + str(user_id) + " " + penalty + "d", level=lvl, chat_id=chat_id)
    except errors.ChatAdminRequired:
        err = "No permission to " + penalty + "."
        if sent_msg:
            await sent_msg.edit_text(err)
        else:
            await client.send_message(send_to or chat_id, err)


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
