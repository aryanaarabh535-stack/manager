from datetime import datetime, timedelta, timezone
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from app.db import database
from app.models import WARNINGS
from app.services.permissions import require_admin, target_user

router = Router()

def parse_duration(value: str) -> timedelta | None:
    try:
        amount, unit = int(value[:-1]), value[-1].lower()
        scale = {"m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
        if amount <= 0 or amount > 3650: return None
        return timedelta(seconds=amount * scale)
    except (ValueError, KeyError, IndexError):
        return None

async def _moderate(message: Message, action: str, timed: bool = False, silent: bool = False, delete_command: bool = False):
    if not await require_admin(message, message.bot, "can_restrict_members"):
        return
    args = (message.text or "").split(maxsplit=2)
    target_arg = args[1] if len(args) > 1 else None
    duration = None
    reason = ""
    if timed and target_arg and parse_duration(target_arg):
        duration = parse_duration(target_arg); target_arg = args[2] if len(args) > 2 else None
    elif len(args) > 2:
        reason = args[2]
    target = await target_user(message, target_arg)
    if not target:
        await message.reply("Reply to the user's message or provide a numeric user ID. Usage: /" + message.text.split()[0][1:] + " [duration] [user_id] [reason]")
        return
    try:
        if action == "ban":
            until = datetime.now(timezone.utc) + duration if duration else None
            await message.bot.ban_chat_member(message.chat.id, target, until_date=until)
        elif action == "unban":
            await message.bot.unban_chat_member(message.chat.id, target, only_if_banned=True)
        elif action == "mute":
            until = datetime.now(timezone.utc) + duration if duration else None
            await message.bot.restrict_chat_member(message.chat.id, target, permissions=ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False), until_date=until)
        elif action == "unmute":
            await message.bot.restrict_chat_member(message.chat.id, target, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        elif action == "kick":
            await message.bot.ban_chat_member(message.chat.id, target)
            await message.bot.unban_chat_member(message.chat.id, target, only_if_banned=True)
        if delete_command:
            try: await message.delete()
            except Exception: pass
        if not silent:
            await message.answer(f"✅ User <code>{target}</code> {action}ned." if action in ("ban", "unban") else f"✅ User <code>{target}</code>: {action} completed.", parse_mode="HTML")
    except Exception as exc:
        await message.reply(f"Could not {action} this user: {str(exc)[:250]}")

for cmd, action, timed, silent, delete_cmd in [
    ("ban","ban",False,False,False),("tban","ban",True,False,False),("sban","ban",False,True,False),("dban","ban",False,False,True),("unban","unban",False,False,False),
    ("mute","mute",False,False,False),("tmute","mute",True,False,False),("smute","mute",False,True,False),("dmute","mute",False,False,True),("unmute","unmute",False,False,False),
    ("kick","kick",False,False,False),("skick","kick",False,True,False),("dkick","kick",False,False,True)]:
    async def handler(message: Message, _a=action, _t=timed, _s=silent, _d=delete_cmd):
        await _moderate(message, _a, _t, _s, _d)
    router.message.register(handler, Command(cmd))

@router.message(Command("setwarnlimit"))
async def setwarnlimit(message: Message):
    if not await require_admin(message, message.bot, "can_restrict_members"): return
    parts=(message.text or "").split()
    if len(parts)<2 or not parts[1].isdigit(): return await message.reply("Usage: /setwarnlimit <number> (0 disables automatic action)")
    from app.models import CHAT_SETTINGS
    from app.db import database
    limit=max(0,min(20,int(parts[1])))
    await database[CHAT_SETTINGS].update_one({"chat_id":message.chat.id},{"$set":{"warn_limit":limit}},upsert=True)
    await message.reply(f"Warning threshold set to {limit}.")

@router.message(Command("setwarnaction"))
async def setwarnaction(message: Message):
    if not await require_admin(message, message.bot, "can_restrict_members"): return
    parts=(message.text or "").split()
    if len(parts)<2 or parts[1] not in ("mute","ban","kick"): return await message.reply("Usage: /setwarnaction mute|ban|kick")
    from app.models import CHAT_SETTINGS
    from app.db import database
    await database[CHAT_SETTINGS].update_one({"chat_id":message.chat.id},{"$set":{"warn_action":parts[1]}},upsert=True)
    await message.reply("Automatic warning action saved.")

@router.message(Command("warn"))
async def warn(message: Message):
    if not await require_admin(message, message.bot, "can_restrict_members"): return
    parts = (message.text or "").split(maxsplit=1)
    argument = parts[1] if len(parts) > 1 else None
    target = await target_user(message, argument.split(maxsplit=1)[0] if argument and not message.reply_to_message else None)
    if not target:
        await message.reply("Reply to a user or provide a numeric ID. Usage: /warn [user_id] [reason]"); return
    reason = (argument.split(maxsplit=1)[1] if argument and not message.reply_to_message and len(argument.split(maxsplit=1)) > 1 else argument if message.reply_to_message else None)
    await database[WARNINGS].insert_one({"chat_id": message.chat.id, "user_id": target, "admin_id": message.from_user.id, "reason": reason, "created_at": datetime.now(timezone.utc)})
    count = await database[WARNINGS].count_documents({"chat_id": message.chat.id, "user_id": target})
    from app.models import CHAT_SETTINGS
    row=await database[CHAT_SETTINGS].find_one({"chat_id":message.chat.id}) or {}
    limit=int(row.get("warn_limit",3) or 0); action=row.get("warn_action","mute")
    outcome=""
    if limit and count>=limit:
        try:
            if action=="ban": await message.bot.ban_chat_member(message.chat.id,target)
            elif action=="kick":
                await message.bot.ban_chat_member(message.chat.id,target); await message.bot.unban_chat_member(message.chat.id,target)
            else: await message.bot.restrict_chat_member(message.chat.id,target,permissions=ChatPermissions(can_send_messages=False),until_date=datetime.now(timezone.utc)+timedelta(hours=1))
            await database[WARNINGS].delete_many({"chat_id":message.chat.id,"user_id":target})
            outcome=f"\nThreshold reached: {action} applied and warnings reset."
        except Exception as exc: outcome=f"\nCould not apply automatic action: {str(exc)[:120]}"
    await message.reply(f"⚠️ User <code>{target}</code> warned. Total warnings: <b>{count}</b>{outcome}", parse_mode="HTML")

@router.message(Command("warns"))
async def warns(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    target = await target_user(message, parts[1] if len(parts) > 1 else None)
    if not target: await message.reply("Reply to a user or provide a numeric ID."); return
    rows = await database[WARNINGS].find({"chat_id": message.chat.id, "user_id": target}).sort("created_at", -1).limit(20).to_list(length=20)
    total = await database[WARNINGS].count_documents({"chat_id": message.chat.id, "user_id": target})
    await message.reply(f"Warnings for <code>{target}</code>: <b>{total}</b> (showing up to {len(rows)})", parse_mode="HTML")

@router.message(Command("resetwarns"))
async def resetwarns(message: Message):
    if not await require_admin(message, message.bot, "can_restrict_members"): return
    parts = (message.text or "").split(maxsplit=1)
    target = await target_user(message, parts[1] if len(parts) > 1 else None)
    if not target: await message.reply("Reply to a user or provide a numeric ID."); return
    await database[WARNINGS].delete_many({"chat_id": message.chat.id, "user_id": target})
    await message.reply("✅ Warnings reset.")
