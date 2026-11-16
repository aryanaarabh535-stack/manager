from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db import database
from app.models import SAVED_ITEMS
from app.services.permissions import require_admin

router = Router()

@router.message(Command("save"))
async def save(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3: await message.reply("Usage: /save <single_word_trigger> <content>"); return
    trigger, content = parts[1].lstrip("#"), parts[2]
    await database[SAVED_ITEMS].update_one({"chat_id": message.chat.id, "kind": "note", "trigger": trigger}, {"$set": {"content": content, "created_by": message.from_user.id}, "$setOnInsert": {"chat_id": message.chat.id, "kind": "note", "trigger": trigger}}, upsert=True)
    await message.reply(f"✅ Note <code>{trigger}</code> saved.", parse_mode="HTML")

@router.message(Command("get"))
async def get_note(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2: await message.reply("Usage: /get <trigger>"); return
    item = await database[SAVED_ITEMS].find_one({"chat_id": message.chat.id, "kind": "note", "trigger": parts[1]})
    await message.reply(item["content"] if item else "Note not found.")

@router.message(Command("notes"))
async def notes(message: Message):
    rows = await database[SAVED_ITEMS].find({"chat_id": message.chat.id, "kind": "note"}, {"trigger": 1, "_id": 0}).sort("trigger", 1).to_list(length=500)
    await message.reply("Saved notes:\\n" + ("\\n".join(f"• {x['trigger']}" for x in rows) if rows else "No notes saved."))

@router.message(Command("clear"))
async def clear(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2: await message.reply("Usage: /clear <trigger>"); return
    await database[SAVED_ITEMS].delete_one({"chat_id": message.chat.id, "kind": "note", "trigger": parts[1]}); await message.reply("✅ Note removed (if it existed).")

@router.message(Command("filter"))
async def filter_add(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3: await message.reply('Usage: /filter <word or "phrase"> <reply>'); return
    trigger, content = parts[1].strip('"'), parts[2]
    await database[SAVED_ITEMS].update_one({"chat_id": message.chat.id, "kind": "filter", "trigger": trigger}, {"$set": {"content": content, "created_by": message.from_user.id}, "$setOnInsert": {"chat_id": message.chat.id, "kind": "filter", "trigger": trigger}}, upsert=True)
    await message.reply("✅ Filter saved.")

@router.message(Command("filters"))
async def filters(message: Message):
    rows = await database[SAVED_ITEMS].find({"chat_id": message.chat.id, "kind": "filter"}, {"trigger": 1, "_id": 0}).sort("trigger", 1).to_list(length=500)
    await message.reply("Filters:\\n" + ("\\n".join(f"• {x['trigger']}" for x in rows) if rows else "No filters saved."))

@router.message(Command("stop"))
async def stop_filter(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"): return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2: await message.reply("Usage: /stop <trigger>"); return
    await database[SAVED_ITEMS].delete_one({"chat_id": message.chat.id, "kind": "filter", "trigger": parts[1].strip('"')}); await message.reply("✅ Filter removed (if it existed).")
