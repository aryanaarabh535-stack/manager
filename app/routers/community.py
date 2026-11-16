from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db import database
from app.models import CHAT_SETTINGS
from app.services.permissions import require_admin

router = Router()
DEFAULTS = {"welcome_enabled": False, "goodbye_enabled": False, "welcome_text": None, "goodbye_text": None, "rules_text": None, "private_rules": True, "private_notes": False, "captcha_enabled": False, "flood_limit": 0, "flood_action": "mute", "antiraid_enabled": False, "warn_limit": 3, "warn_action": "mute", "raid_threshold": 8, "raid_action": "ban", "captcha_timeout_minutes": 5, "locks": {}, "options": {}}

async def get_settings(chat_id: int) -> dict:
    await database[CHAT_SETTINGS].update_one({"chat_id": chat_id}, {"$setOnInsert": {"chat_id": chat_id, **DEFAULTS}}, upsert=True)
    return await database[CHAT_SETTINGS].find_one({"chat_id": chat_id})

@router.message(Command("welcome"))
async def welcome(message: Message):
    obj = await get_settings(message.chat.id); args = (message.text or "").split(maxsplit=1)
    if len(args) == 1 or args[1].lower() == "noformat":
        await message.reply(f"Welcome is {'ON' if obj.get('welcome_enabled') else 'OFF'}.\\nText: {obj.get('welcome_text') or 'Default welcome'}"); return
    if not await require_admin(message, message.bot, "can_change_info"): return
    value = args[1].lower()
    if value in ("on", "yes", "true", "off", "no", "false"):
        enabled = value in ("on", "yes", "true"); await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"welcome_enabled": enabled}}, upsert=True)
        await message.reply("Welcome " + ("enabled" if enabled else "disabled") + ".")

@router.message(Command("setwelcome"))
async def setwelcome(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"welcome_text": (message.text or "").partition(" ")[2] or None}}, upsert=True)
    await message.reply("✅ Welcome message saved.")

@router.message(Command("goodbye"))
async def goodbye(message: Message):
    args = (message.text or "").split(maxsplit=1); row = await get_settings(message.chat.id)
    if len(args) == 1: await message.reply(f"Goodbye is {'ON' if row.get('goodbye_enabled') else 'OFF'}."); return
    if not await require_admin(message, message.bot, "can_change_info"): return
    await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"goodbye_enabled": args[1].lower() in ("on", "yes", "true")}}, upsert=True)
    await message.reply("Goodbye setting updated.")

@router.message(Command("setgoodbye"))
async def setgoodbye(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"goodbye_text": (message.text or "").partition(" ")[2] or None}}, upsert=True)
    await message.reply("✅ Goodbye message saved.")

@router.message(Command("rules"))
async def rules(message: Message):
    row = await get_settings(message.chat.id); await message.reply(row.get("rules_text") or "No rules have been configured yet.")

@router.message(Command("setrules"))
async def setrules(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    value = (message.text or "").partition(" ")[2]
    if not value: await message.reply("Usage: /setrules <rules text>"); return
    await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"rules_text": value}}, upsert=True); await message.reply("✅ Group rules saved.")

@router.message(Command("resetrules"))
async def resetrules(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    await database[CHAT_SETTINGS].update_one({"chat_id": message.chat.id}, {"$set": {"rules_text": None}}, upsert=True); await message.reply("✅ Rules removed.")
