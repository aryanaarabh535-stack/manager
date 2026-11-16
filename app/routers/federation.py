from datetime import datetime, timezone
from secrets import token_urlsafe

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import database
from app.models import FEDERATIONS, FEDERATION_BANS, FEDERATION_CHATS
from app.services.permissions import require_admin, target_user

router = Router()


async def _group_admin(message: Message) -> bool:
    return await require_admin(message, message.bot, "can_restrict_members")


async def _current_fed(chat_id: int):
    link = await database[FEDERATION_CHATS].find_one({"chat_id": chat_id})
    if not link:
        return None, None
    fed = await database[FEDERATIONS].find_one({"_id": link["federation_id"]})
    return link, fed


async def _is_fed_admin(fed: dict, user_id: int) -> bool:
    return bool(fed and (fed.get("owner_id") == user_id or user_id in fed.get("admins", [])))


@router.message(Command("newfed"))
async def newfed(m: Message):
    if not await _group_admin(m):
        return
    link, _ = await _current_fed(m.chat.id)
    if link:
        return await m.reply("This group is already connected to a federation. Use /leavefed first.")
    p = (m.text or "").split(maxsplit=1)
    name = p[1].strip() if len(p) > 1 else "MANAGER federation"
    public = token_urlsafe(8).replace("-", "").replace("_", "")[:12]
    res = await database[FEDERATIONS].insert_one({
        "name": name, "public_id": public, "owner_id": m.from_user.id,
        "admins": [m.from_user.id], "created_at": datetime.now(timezone.utc),
    })
    await database[FEDERATION_CHATS].insert_one({"chat_id": m.chat.id, "federation_id": res.inserted_id, "joined_by": m.from_user.id, "joined_at": datetime.now(timezone.utc)})
    await m.reply(f"Federation created: <b>{name}</b>\nID: <code>{public}</code>\nOther groups can join with /joinfed {public}", parse_mode="HTML")


@router.message(Command("joinfed"))
async def joinfed(m: Message):
    if not await _group_admin(m):
        return
    p = (m.text or "").split(maxsplit=1)
    if len(p) < 2:
        return await m.reply("Usage: /joinfed FEDERATION_ID")
    link, _ = await _current_fed(m.chat.id)
    if link:
        return await m.reply("This group already belongs to a federation. Use /leavefed first.")
    fed = await database[FEDERATIONS].find_one({"public_id": p[1].strip()})
    if not fed:
        return await m.reply("Federation not found.")
    await database[FEDERATION_CHATS].insert_one({"chat_id": m.chat.id, "federation_id": fed["_id"], "joined_by": m.from_user.id, "joined_at": datetime.now(timezone.utc)})
    # Enforce current federation bans in the newly connected chat where possible.
    bans = await database[FEDERATION_BANS].find({"federation_id": fed["_id"]}).to_list(1000)
    applied = 0
    for ban in bans:
        try:
            await m.bot.ban_chat_member(m.chat.id, ban["user_id"])
            applied += 1
        except Exception:
            pass
    await m.reply(f"Connected this group to {fed['name']}. Existing federation bans applied: {applied}/{len(bans)}.")


@router.message(Command("leavefed"))
async def leavefed(m: Message):
    if not await _group_admin(m):
        return
    link, _ = await _current_fed(m.chat.id)
    if not link:
        return await m.reply("This group is not in a federation.")
    await database[FEDERATION_CHATS].delete_one({"chat_id": m.chat.id})
    await m.reply("This group left its federation. Existing bans in this group are not automatically reversed.")


@router.message(Command("fedinfo"))
async def fedinfo(m: Message):
    _, fed = await _current_fed(m.chat.id)
    if not fed:
        return await m.reply("This group is not in a federation.")
    chats = await database[FEDERATION_CHATS].count_documents({"federation_id": fed["_id"]})
    bans = await database[FEDERATION_BANS].count_documents({"federation_id": fed["_id"]})
    await m.reply(f"<b>{fed['name']}</b>\nID: <code>{fed['public_id']}</code>\nConnected groups: {chats}\nFederation admins: {len(fed.get('admins', []))}\nActive federation bans: {bans}", parse_mode="HTML")


@router.message(Command("fedadmins"))
async def fedadmins(m: Message):
    _, fed = await _current_fed(m.chat.id)
    if not fed:
        return await m.reply("This group is not in a federation.")
    await m.reply("Federation admin IDs:\n" + "\n".join(f"• <code>{uid}</code>" for uid in fed.get("admins", [])), parse_mode="HTML")


@router.message(Command("addfedadmin"))
async def addfedadmin(m: Message):
    if not await _group_admin(m):
        return
    _, fed = await _current_fed(m.chat.id)
    if not fed:
        return await m.reply("This group is not in a federation.")
    if fed.get("owner_id") != m.from_user.id:
        return await m.reply("Only the federation owner can add federation administrators.")
    p = (m.text or "").split(maxsplit=1)
    uid = await target_user(m, p[1] if len(p) > 1 else None)
    if not uid:
        return await m.reply("Reply to a user or use /addfedadmin USER_ID")
    await database[FEDERATIONS].update_one({"_id": fed["_id"]}, {"$addToSet": {"admins": uid}})
    await m.reply(f"Added <code>{uid}</code> as a federation admin.", parse_mode="HTML")


@router.message(Command("delfedadmin"))
async def delfedadmin(m: Message):
    if not await _group_admin(m):
        return
    _, fed = await _current_fed(m.chat.id)
    if not fed:
        return await m.reply("This group is not in a federation.")
    if fed.get("owner_id") != m.from_user.id:
        return await m.reply("Only the federation owner can remove federation administrators.")
    p = (m.text or "").split(maxsplit=1)
    uid = await target_user(m, p[1] if len(p) > 1 else None)
    if not uid:
        return await m.reply("Reply to a user or use /delfedadmin USER_ID")
    if uid == fed.get("owner_id"):
        return await m.reply("The federation owner cannot be removed from the admin list.")
    await database[FEDERATIONS].update_one({"_id": fed["_id"]}, {"$pull": {"admins": uid}})
    await m.reply("Federation administrator removed.")


@router.message(Command("fban"))
async def fban(m: Message):
    if not await _group_admin(m):
        return
    link, fed = await _current_fed(m.chat.id)
    if not link or not fed:
        return await m.reply("Join a federation first.")
    if not await _is_fed_admin(fed, m.from_user.id):
        return await m.reply("You must be a federation administrator to issue federation bans.")
    p = (m.text or "").split(maxsplit=2)
    uid = await target_user(m, p[1] if len(p) > 1 else None)
    if not uid:
        return await m.reply("Reply to a user or use /fban USER_ID [reason]")
    reason = p[2] if len(p) > 2 else ""
    await database[FEDERATION_BANS].update_one(
        {"federation_id": fed["_id"], "user_id": uid},
        {"$set": {"reason": reason, "by": m.from_user.id, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    chats = await database[FEDERATION_CHATS].find({"federation_id": fed["_id"]}).to_list(500)
    success, failed = [], []
    for chat in chats:
        try:
            await m.bot.ban_chat_member(chat["chat_id"], uid)
            success.append(chat["chat_id"])
        except Exception:
            failed.append(chat["chat_id"])
    await m.reply(f"Federation ban saved for <code>{uid}</code>.\nBanned: {len(success)}/{len(chats)} groups.\nCould not apply: {len(failed)}.", parse_mode="HTML")


@router.message(Command("unfban"))
async def unfban(m: Message):
    if not await _group_admin(m):
        return
    link, fed = await _current_fed(m.chat.id)
    if not link or not fed:
        return await m.reply("Join a federation first.")
    if not await _is_fed_admin(fed, m.from_user.id):
        return await m.reply("You must be a federation administrator to remove federation bans.")
    p = (m.text or "").split(maxsplit=1)
    uid = await target_user(m, p[1] if len(p) > 1 else None)
    if not uid:
        return await m.reply("Reply to a user or use /unfban USER_ID")
    await database[FEDERATION_BANS].delete_one({"federation_id": fed["_id"], "user_id": uid})
    chats = await database[FEDERATION_CHATS].find({"federation_id": fed["_id"]}).to_list(500)
    success = 0
    for chat in chats:
        try:
            await m.bot.unban_chat_member(chat["chat_id"], uid, only_if_banned=True)
            success += 1
        except Exception:
            pass
    await m.reply(f"Federation ban removed. Unban attempted in {success}/{len(chats)} groups.")


@router.message(Command("delfed"))
async def delfed(m: Message):
    if not await _group_admin(m):
        return
    link, fed = await _current_fed(m.chat.id)
    if not link or not fed:
        return await m.reply("This group is not in a federation.")
    if fed.get("owner_id") != m.from_user.id:
        return await m.reply("Only the federation owner can delete it.")
    await database[FEDERATION_CHATS].delete_many({"federation_id": fed["_id"]})
    await database[FEDERATION_BANS].delete_many({"federation_id": fed["_id"]})
    await database[FEDERATIONS].delete_one({"_id": fed["_id"]})
    await m.reply("Federation deleted. Existing Telegram bans are not automatically reversed.")
