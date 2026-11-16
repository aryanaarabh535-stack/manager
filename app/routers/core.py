from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.db import database
from app.keyboards import settings_keyboard
from app.models import CHAT_SETTINGS
from app.routers.community import get_settings

router = Router()
PAGES = {"main", "moderation", "security", "greetings", "content", "community", "federation", "logs", "general"}
TOGGLES = {
    "toggle_welcome": "welcome_enabled", "toggle_goodbye": "goodbye_enabled",
    "toggle_captcha": "captcha_enabled", "toggle_antiraid": "antiraid_enabled",
}
LOCK_TOGGLES = {f"toggle_lock_{kind}": kind for kind in ("text", "media", "links", "photo", "video", "sticker", "document")}
HELP_TEXT = {
    "help_warnings": "Use /warn (reply or user ID), /warns, /resetwarns, /setwarnlimit N and /setwarnaction mute|ban|kick.",
    "help_approvals": "Use /approve (reply or user ID), /unapprove and /approved.",
    "help_admins": "Use /adminlist, /adminrights (reply or user ID), /admincache, /promote and /demote.",
    "help_purge": "Reply to the first message and use /purge. The current implementation attempts up to 100 message deletions.",
    "help_blocklist": "Use /addblocklist <phrase> or /addblocklist word|regex <pattern>, /unblocklist <phrase> and /blocklist.",
    "help_antiflood": "Use /setflood N (messages per 5 seconds; 0 disables) and /setfloodaction delete|mute|ban|kick. Use /antiraid on|off, /setraidthreshold N and /setraidaction ban|kick|mute.",
    "help_setwelcome": "Use /setwelcome <text> and /welcome on|off.",
    "help_setgoodbye": "Use /setgoodbye <text> and /goodbye on|off.",
    "help_notes": "Use /save <trigger> <text>, /get <trigger>, /notes and /clear <trigger>.",
    "help_filters": "Use /filter <trigger> <reply>, /filters and /stop <trigger>.",
    "help_rules": "Use /rules to view the current group rules.",
    "help_setrules": "Use /setrules <text> and /resetrules.",
    "help_reports": "Reply to a message with /report [reason]. Admins can use /reports to list open reports.",
    "help_fed": "Use /newfed, /joinfed ID, /leavefed, /fedinfo, /fedadmins, /addfedadmin, /delfedadmin, /fban, /unfban and /delfed.",
    "help_setlog": "Use /setlog CHAT_ID after adding MANAGER to the destination chat.",
    "help_admincache": "Use /admincache to refresh the cached administrator list.",
    "help_connections": "Connected-chat management is not implemented in this build yet.",
}


@router.message(CommandStart())
async def start(message: Message):
    await message.answer("🌹 <b>MANAGER</b>\nAdvanced group management bot. Add me to your group and grant the administrator permissions it needs, then use /help.", parse_mode="HTML")


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("<b>MANAGER command families</b>\nModeration: /ban /mute /kick /warn\nSecurity: /lock /blocklist /setflood /captcha /antiraid\nCommunity: /welcome /goodbye /rules /report\nContent: /save /get /filter\nFederation: /newfed /joinfed /fban\nUse /settings for the interactive panel.", parse_mode="HTML")


@router.message(Command("settings"))
async def settings(message: Message):
    if message.chat.type == "private":
        return await message.answer("Open /settings inside the group you want to configure.")
    row = await get_settings(message.chat.id)
    await message.answer("⚙️ <b>MANAGER settings</b>\nChoose a module:", reply_markup=settings_keyboard("main", row), parse_mode="HTML")


@router.callback_query(F.data.startswith("mgr:"))
async def settings_callback(query: CallbackQuery):
    key = query.data.split(":", 1)[1]
    chat_id = query.message.chat.id if query.message else None
    if not chat_id:
        return await query.answer("Settings message unavailable.", show_alert=True)
    if key in PAGES:
        row = await get_settings(chat_id)
        await query.message.edit_reply_markup(reply_markup=settings_keyboard(key, row))
        return await query.answer()
    if key in TOGGLES or key in LOCK_TOGGLES:
        try:
            member = await query.bot.get_chat_member(chat_id, query.from_user.id)
            if member.status not in ("administrator", "creator"):
                return await query.answer("Group administrators only.", show_alert=True)
            field = TOGGLES.get(key)
            if field:
                if field in ("captcha_enabled", "antiraid_enabled") and member.status != "creator" and not getattr(member, "can_restrict_members", False):
                    return await query.answer("You need permission to restrict members.", show_alert=True)
                row = await get_settings(chat_id)
                enabled = not bool(row.get(field, False))
                await database[CHAT_SETTINGS].update_one({"chat_id": chat_id}, {"$set": {field: enabled}}, upsert=True)
            else:
                if member.status != "creator" and not getattr(member, "can_restrict_members", False):
                    return await query.answer("You need permission to restrict members.", show_alert=True)
                kind = LOCK_TOGGLES[key]
                row = await get_settings(chat_id)
                enabled = not bool(row.get("locks", {}).get(kind, False))
                await database[CHAT_SETTINGS].update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id, f"locks.{kind}": enabled}}, upsert=True)
            row = await get_settings(chat_id)
            page = "security" if key.startswith("toggle_lock_") or key == "toggle_captcha" or key == "toggle_antiraid" else "greetings"
            await query.message.edit_reply_markup(reply_markup=settings_keyboard(page, row))
            return await query.answer(("Enabled" if enabled else "Disabled") + ".")
        except Exception:
            return await query.answer("Could not update this setting. Check bot permissions.", show_alert=True)
    if key in HELP_TEXT:
        return await query.answer(HELP_TEXT[key], show_alert=True)
    await query.answer("This panel item is not available yet.", show_alert=True)
