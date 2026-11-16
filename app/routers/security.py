from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, ChatMemberUpdated, ChatPermissions, InlineKeyboardButton,
    InlineKeyboardMarkup, Message,
)

from app.db import database
from app.models import APPROVED_USERS, BLOCKLIST_ENTRIES, CHAT_SETTINGS, SAVED_ITEMS
from app.routers.community import get_settings
from app.services.permissions import require_admin
from app.services.security import LOCK_TYPES, blocklist_matches, message_matches_lock

router = Router()
LOCK_MAP = {name: name for name in LOCK_TYPES}


def _args(message: Message) -> list[str]:
    return (message.text or "").split(maxsplit=1)


async def _set_chat_value(chat_id: int, field: str, value) -> None:
    await database[CHAT_SETTINGS].update_one(
        {"chat_id": chat_id}, {"$set": {"chat_id": chat_id, field: value}}, upsert=True
    )


@router.message(Command("lock"))
async def lock_cmd(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    kind = p[1].lower() if len(p) > 1 else ""
    if kind not in LOCK_MAP:
        return await m.reply("Usage: /lock " + " | ".join(LOCK_TYPES))
    await _set_chat_value(m.chat.id, f"locks.{kind}", True)
    await m.reply(f"🔒 Locked {kind}.")


@router.message(Command("unlock"))
async def unlock_cmd(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    kind = p[1].lower() if len(p) > 1 else ""
    if kind not in LOCK_MAP:
        return await m.reply("Usage: /unlock " + " | ".join(LOCK_TYPES))
    await _set_chat_value(m.chat.id, f"locks.{kind}", False)
    await m.reply(f"🔓 Unlocked {kind}.")


@router.message(Command("locktypes"))
async def locktypes(m: Message):
    await m.reply("Lock types:\n" + ", ".join(LOCK_TYPES))


@router.message(Command("addblocklist"))
async def addblocklist(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split(maxsplit=2)
    if len(p) < 2:
        return await m.reply("Usage: /addblocklist [contains|word|regex] <phrase>")
    explicit_mode = p[1].lower() in ("contains", "word", "regex")
    mode = p[1].lower() if explicit_mode else "contains"
    phrase = (p[2].strip() if len(p) == 3 else "") if explicit_mode else " ".join(p[1:]).strip()
    if not phrase:
        return await m.reply("Please provide a phrase or pattern.")
    if mode == "regex":
        import re
        try:
            re.compile(phrase)
        except re.error as exc:
            return await m.reply(f"Invalid regular expression: {exc}")
    await database[BLOCKLIST_ENTRIES].update_one(
        {"chat_id": m.chat.id, "phrase": phrase},
        {"$set": {"mode": mode, "created_by": m.from_user.id}}, upsert=True,
    )
    await m.reply(f"Added blocklist entry ({mode}): <code>{phrase}</code>", parse_mode="HTML")


@router.message(Command("unblocklist"))
async def unblocklist(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    if len(p) < 2:
        return await m.reply("Usage: /unblocklist <phrase>")
    result = await database[BLOCKLIST_ENTRIES].delete_one({"chat_id": m.chat.id, "phrase": p[1].strip()})
    await m.reply("Removed." if result.deleted_count else "Entry not found.")


@router.message(Command("blocklist"))
async def blocklist(m: Message):
    rows = await database[BLOCKLIST_ENTRIES].find({"chat_id": m.chat.id}).sort("phrase", 1).to_list(200)
    if not rows:
        return await m.reply("Blocklist is empty.")
    lines = [f"• <code>{x['phrase']}</code> ({x.get('mode', 'contains')})" for x in rows]
    await m.reply("<b>Blocked terms</b>\n" + "\n".join(lines), parse_mode="HTML")


@router.message(Command("setflood"))
async def setflood(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split()
    if len(p) < 2 or not p[1].isdigit():
        return await m.reply("Usage: /setflood <messages per 5 seconds> (0 disables)")
    n = max(0, min(50, int(p[1])))
    await _set_chat_value(m.chat.id, "flood_limit", n)
    await m.reply(f"Antiflood limit set to {n} messages per 5 seconds.")


@router.message(Command("setfloodaction"))
async def setfloodaction(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split()
    if len(p) < 2 or p[1] not in ("delete", "mute", "ban", "kick"):
        return await m.reply("Usage: /setfloodaction delete|mute|ban|kick")
    await _set_chat_value(m.chat.id, "flood_action", p[1])
    await m.reply("Flood action saved.")


@router.message(Command("antiraid"))
async def antiraid(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    value = p[1].lower() if len(p) > 1 else "status"
    if value not in ("on", "off", "status"):
        return await m.reply("Usage: /antiraid on|off|status")
    if value != "status":
        await _set_chat_value(m.chat.id, "antiraid_enabled", value == "on")
    row = await get_settings(m.chat.id)
    await m.reply("Anti-raid is " + ("ON" if row.get("antiraid_enabled") else "OFF"))


@router.message(Command("setraidthreshold"))
async def setraidthreshold(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split()
    if len(p) < 2 or not p[1].isdigit():
        return await m.reply("Usage: /setraidthreshold <joins in 10 seconds>")
    n = max(2, min(100, int(p[1])))
    await _set_chat_value(m.chat.id, "raid_threshold", n)
    await m.reply(f"Anti-raid threshold set to {n} joins per 10 seconds.")


@router.message(Command("setraidaction"))
async def setraidaction(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split()
    if len(p) < 2 or p[1] not in ("ban", "kick", "mute"):
        return await m.reply("Usage: /setraidaction ban|kick|mute")
    await _set_chat_value(m.chat.id, "raid_action", p[1])
    await m.reply("Anti-raid action saved.")


@router.message(Command("setcaptchatimeout"))
async def setcaptchatimeout(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = (m.text or "").split()
    if len(p) < 2 or not p[1].isdigit():
        return await m.reply("Usage: /setcaptchatimeout <minutes> (1-60)")
    minutes = max(1, min(60, int(p[1])))
    await _set_chat_value(m.chat.id, "captcha_timeout_minutes", minutes)
    await m.reply(f"CAPTCHA timeout set to {minutes} minutes. Expired users are not automatically kicked in this build.")


@router.message(Command("captcha"))
async def captcha(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    value = p[1].lower() if len(p) > 1 else "status"
    if value not in ("on", "off", "status"):
        return await m.reply("Usage: /captcha on|off|status")
    if value != "status":
        await _set_chat_value(m.chat.id, "captcha_enabled", value == "on")
    row = await get_settings(m.chat.id)
    await m.reply("CAPTCHA is " + ("ON" if row.get("captcha_enabled") else "OFF"))


@router.callback_query(F.data.startswith("cap:"))
async def captcha_callback(q: CallbackQuery):
    try:
        _, chat_s, user_s = q.data.split(":", 2)
        chat_id, user_id = int(chat_s), int(user_s)
    except (ValueError, AttributeError):
        return await q.answer("Invalid verification request.", show_alert=True)
    if q.from_user.id != user_id:
        return await q.answer("This verification is not for you.", show_alert=True)
    pending = await database.captcha_pending.find_one({"chat_id": chat_id, "user_id": user_id})
    if not pending or pending.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)) < datetime.now(timezone.utc):
        await database.captcha_pending.delete_one({"chat_id": chat_id, "user_id": user_id})
        return await q.answer("This verification has expired. Please ask an admin to let you rejoin.", show_alert=True)
    try:
        member = await q.bot.get_chat_member(chat_id, user_id)
        if member.status not in ("member", "restricted"):
            return await q.answer("You are no longer a member of this group.", show_alert=True)
        await q.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await database.captcha_pending.delete_one({"chat_id": chat_id, "user_id": user_id})
        if q.message:
            await q.message.edit_text("✅ Verification complete. Welcome!")
    except Exception:
        return await q.answer("Could not verify. Please contact an administrator.", show_alert=True)
    await q.answer("Verified!")


async def process_security_join(event: ChatMemberUpdated):
    old, new = event.old_chat_member.status, event.new_chat_member.status
    if old not in ("left", "kicked") or new not in ("member", "restricted"):
        return
    user = event.new_chat_member.user
    if user.is_bot:
        return
    row = await get_settings(event.chat.id)
    now = datetime.now(timezone.utc)
    if row.get("antiraid_enabled"):
        await database.raid_events.insert_one({"chat_id": event.chat.id, "user_id": user.id, "created_at": now})
        cutoff = now - timedelta(seconds=10)
        recent = await database.raid_events.count_documents({"chat_id": event.chat.id, "created_at": {"$gte": cutoff}})
        threshold = int(row.get("raid_threshold", 8))
        if recent >= threshold:
            action = row.get("raid_action", "ban")
            try:
                if action == "mute":
                    await event.bot.restrict_chat_member(event.chat.id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=now + timedelta(minutes=10))
                else:
                    await event.bot.ban_chat_member(event.chat.id, user.id)
                    if action == "kick":
                        await event.bot.unban_chat_member(event.chat.id, user.id)
            except Exception:
                pass
            return
    if row.get("captcha_enabled"):
        expires = now + timedelta(minutes=int(row.get("captcha_timeout_minutes", 5)))
        try:
            await event.bot.restrict_chat_member(
                event.chat.id, user.id,
                permissions=ChatPermissions(
                    can_send_messages=False, can_send_audios=False, can_send_documents=False,
                    can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
                    can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
            )
            await database.captcha_pending.update_one(
                {"chat_id": event.chat.id, "user_id": user.id},
                {"$set": {"chat_id": event.chat.id, "user_id": user.id, "created_at": now, "expires_at": expires}},
                upsert=True,
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="I am human ✓", callback_data=f"cap:{event.chat.id}:{user.id}")]])
            await event.bot.send_message(event.chat.id, f"Welcome! {user.mention_html()}, please verify within {int((expires-now).total_seconds()//60)} minutes:", reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


async def _apply_flood_action(m: Message, action: str) -> None:
    uid = m.from_user.id
    await m.delete()
    if action == "ban":
        await m.bot.ban_chat_member(m.chat.id, uid)
    elif action == "kick":
        await m.bot.ban_chat_member(m.chat.id, uid)
        await m.bot.unban_chat_member(m.chat.id, uid)
    elif action == "mute":
        await m.bot.restrict_chat_member(m.chat.id, uid, permissions=ChatPermissions(can_send_messages=False), until_date=int(time.time()) + 300)


@router.message()
async def security_filter(m: Message):
    # This is intentionally the final catch-all in this router. Commands are handled
    # by command handlers above and must be allowed to continue to other routers.
    if m.chat.type not in ("group", "supergroup") or not m.from_user or m.from_user.is_bot:
        return
    if m.text and m.text.startswith("/"):
        return
    uid = m.from_user.id
    row = await get_settings(m.chat.id)
    try:
        member = await m.bot.get_chat_member(m.chat.id, uid)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        return
    if await database[APPROVED_USERS].find_one({"chat_id": m.chat.id, "user_id": uid}):
        return

    for kind, enabled in row.get("locks", {}).items():
        if enabled and message_matches_lock(m, kind):
            try:
                await m.delete()
            except Exception:
                pass
            return

    if m.text:
        entries = await database[BLOCKLIST_ENTRIES].find({"chat_id": m.chat.id}).to_list(300)
        for entry in entries:
            if blocklist_matches(m.text, entry):
                try:
                    await m.delete()
                except Exception:
                    pass
                return

    limit = int(row.get("flood_limit") or 0)
    if limit > 0:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=5)
        await database.flood_events.insert_one({"chat_id": m.chat.id, "user_id": uid, "created_at": now})
        count = await database.flood_events.count_documents({"chat_id": m.chat.id, "user_id": uid, "created_at": {"$gte": cutoff}})
        if count > limit:
            try:
                await _apply_flood_action(m, row.get("flood_action", "mute"))
            except Exception:
                pass
            return

    # Text filters share this handler so the security catch-all cannot swallow them.
    if m.text:
        filters = await database[SAVED_ITEMS].find({"chat_id": m.chat.id, "kind": "filter"}).to_list(300)
        text_value = m.text.casefold()
        for item in filters:
            trigger = str(item.get("trigger", "")).casefold()
            if trigger and trigger in text_value:
                await m.reply(item.get("content", ""))
                return


@router.message(Command("approve"))
async def approve_user(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    uid = m.reply_to_message.from_user.id if m.reply_to_message and m.reply_to_message.from_user else (int(p[1]) if len(p) > 1 and p[1].isdigit() else None)
    if not uid:
        return await m.reply("Reply to a user or use /approve USER_ID")
    await database[APPROVED_USERS].update_one({"chat_id": m.chat.id, "user_id": uid}, {"$set": {"approved_by": m.from_user.id, "approved_at": datetime.now(timezone.utc)}}, upsert=True)
    await m.reply(f"✅ Approved <code>{uid}</code> for this group.", parse_mode="HTML")


@router.message(Command("unapprove"))
async def unapprove_user(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    p = _args(m)
    uid = m.reply_to_message.from_user.id if m.reply_to_message and m.reply_to_message.from_user else (int(p[1]) if len(p) > 1 and p[1].isdigit() else None)
    if not uid:
        return await m.reply("Reply to a user or use /unapprove USER_ID")
    await database[APPROVED_USERS].delete_one({"chat_id": m.chat.id, "user_id": uid})
    await m.reply("Approval removed.")


@router.message(Command("approved"))
async def approved_list(m: Message):
    if not await require_admin(m, m.bot, "can_restrict_members"):
        return
    rows = await database[APPROVED_USERS].find({"chat_id": m.chat.id}).to_list(200)
    await m.reply("Approved users:\n" + ("\n".join(f'• <code>{x["user_id"]}</code>' for x in rows) if rows else "None"), parse_mode="HTML")
