from aiogram import Router
from aiogram.types import ChatMemberUpdated, Message
from app.db import database
from app.models import CHAT_SETTINGS
from app.routers.security import process_security_join

router = Router()

def render(template: str, user, chat) -> str:
    values = {"first": user.first_name or "", "last": user.last_name or "", "fullname": user.full_name or "", "username": f"@{user.username}" if user.username else "", "mention": user.mention_html(), "id": str(user.id), "chatname": chat.title or ""}
    for key, value in values.items(): template = template.replace("{" + key + "}", value)
    return template

@router.chat_member()
async def member_update(event: ChatMemberUpdated):
    old, new = event.old_chat_member.status, event.new_chat_member.status
    joined = old in ("left", "kicked") and new in ("member", "restricted")
    left = old in ("member", "restricted", "administrator") and new in ("left", "kicked")
    if joined:
        await process_security_join(event)
    if not (joined or left): return
    row = await database[CHAT_SETTINGS].find_one({"chat_id": event.chat.id})
    if not row: return
    if joined and row.get("welcome_enabled"):
        await event.bot.send_message(event.chat.id, render(row.get("welcome_text") or "Hey {first}, welcome to {chatname}!", event.new_chat_member.user, event.chat))
    if left and row.get("goodbye_enabled"):
        await event.bot.send_message(event.chat.id, render(row.get("goodbye_text") or "Goodbye {first}!", event.old_chat_member.user, event.chat))

