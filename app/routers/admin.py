from datetime import datetime, timezone

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import Message

from app.db import database
from app.services.permissions import require_admin, target_user

router = Router()


@router.message(Command("promote"))
async def promote(message: Message):
    if not await require_admin(message, message.bot, "can_promote_members"):
        return
    parts = (message.text or "").split(maxsplit=1)
    uid = await target_user(message, parts[1] if len(parts) > 1 else None)
    if not uid:
        return await message.reply("Reply to a user or use /promote USER_ID")
    if uid == message.from_user.id:
        return await message.reply("You cannot promote yourself.")
    try:
        target = await message.bot.get_chat_member(message.chat.id, uid)
        if target.status == ChatMemberStatus.CREATOR:
            return await message.reply("The group owner cannot be promoted or changed.")
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
            can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True,
            can_promote_members=False, can_change_info=False, can_post_messages=False,
            can_edit_messages=False, can_manage_topics=False,
        )
        await database.admin_cache.delete_one({"chat_id": message.chat.id, "user_id": uid})
        await message.reply(f"Promoted <code>{uid}</code> with moderator permissions. Use Telegram's admin editor for any additional rights.", parse_mode="HTML")
    except Exception as exc:
        await message.reply(f"Promotion failed: {str(exc)[:180]}")


@router.message(Command("demote"))
async def demote(message: Message):
    if not await require_admin(message, message.bot, "can_promote_members"):
        return
    parts = (message.text or "").split(maxsplit=1)
    uid = await target_user(message, parts[1] if len(parts) > 1 else None)
    if not uid:
        return await message.reply("Reply to a user or use /demote USER_ID")
    try:
        target = await message.bot.get_chat_member(message.chat.id, uid)
        if target.status == ChatMemberStatus.CREATOR:
            return await message.reply("The group owner cannot be demoted.")
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_change_info=False, can_post_messages=False, can_edit_messages=False,
            can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
            can_pin_messages=False, can_promote_members=False, can_manage_video_chats=False,
            can_manage_chat=False, can_manage_topics=False,
        )
        await database.admin_cache.delete_one({"chat_id": message.chat.id, "user_id": uid})
        await message.reply(f"Demoted <code>{uid}</code>.", parse_mode="HTML")
    except Exception as exc:
        await message.reply(f"Demotion failed: {str(exc)[:180]}")


@router.message(Command("adminlist"))
async def adminlist(message: Message):
    admins = await message.bot.get_chat_administrators(message.chat.id)
    lines = []
    for admin in admins:
        user = admin.user
        if admin.status == ChatMemberStatus.CREATOR:
            role = "owner"
        else:
            rights = [name.removeprefix("can_") for name in (
                "can_delete_messages", "can_restrict_members", "can_promote_members",
                "can_change_info", "can_invite_users", "can_pin_messages", "can_manage_topics",
            ) if getattr(admin, name, False)]
            role = "admin" + (f" ({', '.join(rights)})" if rights else "")
        lines.append(f"• {user.mention_html()} — {role}")
    await message.reply("<b>Group administrators</b>\n" + "\n".join(lines), parse_mode="HTML")


@router.message(Command("admincache"))
async def admincache(message: Message):
    if not await require_admin(message, message.bot, "can_change_info"):
        return
    admins = await message.bot.get_chat_administrators(message.chat.id)
    now = datetime.now(timezone.utc)
    docs = []
    for admin in admins:
        docs.append({
            "chat_id": message.chat.id, "user_id": admin.user.id,
            "status": admin.status,
            "rights": {key: bool(getattr(admin, key, False)) for key in (
                "can_manage_chat", "can_delete_messages", "can_restrict_members",
                "can_promote_members", "can_change_info", "can_invite_users",
                "can_pin_messages", "can_manage_topics", "can_manage_video_chats",
            )},
            "updated_at": now,
        })
    await database.admin_cache.delete_many({"chat_id": message.chat.id})
    if docs:
        await database.admin_cache.insert_many(docs)
    await message.reply(f"Admin cache refreshed: {len(docs)} administrators.")


@router.message(Command("adminrights"))
async def adminrights(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    uid = await target_user(message, parts[1] if len(parts) > 1 else None)
    if not uid:
        return await message.reply("Reply to an administrator or use /adminrights USER_ID")
    try:
        member = await message.bot.get_chat_member(message.chat.id, uid)
    except Exception as exc:
        return await message.reply(f"Could not read admin rights: {str(exc)[:160]}")
    if member.status == ChatMemberStatus.CREATOR:
        return await message.reply("This user is the group owner and has all administrator rights.")
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        return await message.reply("That user is not an administrator.")
    fields = (
        "can_manage_chat", "can_delete_messages", "can_manage_video_chats",
        "can_restrict_members", "can_promote_members", "can_change_info",
        "can_invite_users", "can_pin_messages", "can_manage_topics",
    )
    lines = [f"{'✅' if getattr(member, key, False) else '❌'} {key.removeprefix('can_').replace('_', ' ')}" for key in fields]
    await message.reply(f"<b>Admin rights for {member.user.mention_html()}</b>\n" + "\n".join(lines), parse_mode="HTML")
