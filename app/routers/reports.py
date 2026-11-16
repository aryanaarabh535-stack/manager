from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.db import database
from app.models import CHAT_SETTINGS
from app.services.permissions import require_admin

router = Router()


@router.message(Command("setlog"))
async def setlog(m: Message):
    if not await require_admin(m, m.bot, "can_change_info"):
        return
    p = (m.text or "").split(maxsplit=1)
    if len(p) < 2:
        return await m.reply("Usage: /setlog CHAT_ID (add MANAGER to that channel/group first)")
    try:
        cid = int(p[1])
    except ValueError:
        return await m.reply("Use a numeric channel/group ID.")
    try:
        await m.bot.get_chat(cid)
    except Exception as exc:
        return await m.reply(f"I cannot access that chat: {str(exc)[:150]}")
    await database[CHAT_SETTINGS].update_one({"chat_id": m.chat.id}, {"$set": {"chat_id": m.chat.id, "log_chat_id": cid}}, upsert=True)
    await m.reply("Moderation log destination saved.")


@router.message(Command(commands=["report", "admin"]))
async def report(m: Message):
    if not m.reply_to_message:
        return await m.reply("Reply to the message you want to report, then send /report [reason].")
    if not m.from_user:
        return
    row = await database[CHAT_SETTINGS].find_one({"chat_id": m.chat.id}) or {}
    log_chat = row.get("log_chat_id")
    reason = (m.text or "").partition(" ")[2] or "No reason provided"
    reported = m.reply_to_message.from_user
    report_doc = {
        "chat_id": m.chat.id,
        "message_id": m.reply_to_message.message_id,
        "reported_user_id": reported.id if reported else None,
        "reporter_id": m.from_user.id,
        "reason": reason[:1000],
        "created_at": datetime.now(timezone.utc),
        "status": "open",
    }
    result = await database.reports.insert_one(report_doc)
    report_text = (
        "🚩 <b>New report</b>\n"
        f"Chat: {m.chat.title or m.chat.id}\n"
        f"Reported user: {reported.mention_html() if reported else 'unknown'}\n"
        f"Reported message: <code>{m.reply_to_message.message_id}</code>\n"
        f"By: {m.from_user.mention_html()}\n"
        f"Reason: {reason[:1000]}\n"
        f"Report ID: <code>{str(result.inserted_id)}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Dismiss report", callback_data=f"report:dismiss:{result.inserted_id}")]])
    delivered = False
    if log_chat:
        try:
            await m.bot.send_message(log_chat, report_text, parse_mode="HTML", reply_markup=kb)
            delivered = True
        except Exception:
            pass
    try:
        admins = await m.bot.get_chat_administrators(m.chat.id)
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await m.bot.send_message(admin.user.id, report_text, parse_mode="HTML")
                    delivered = True
                except Exception:
                    pass
    except Exception:
        pass
    await m.reply("🚩 Report recorded and sent to moderators." if delivered else "🚩 Report recorded. Configure /setlog so moderators can receive reports.")


@router.callback_query(F.data.startswith("report:dismiss:"))
async def dismiss(q: CallbackQuery):
    report_id = q.data.split(":", 2)[2]
    try:
        from bson import ObjectId
        oid = ObjectId(report_id)
    except Exception:
        return await q.answer("Invalid report reference.", show_alert=True)
    report_doc = await database.reports.find_one({"_id": oid})
    if not report_doc:
        return await q.answer("Report not found.", show_alert=True)
    try:
        member = await q.bot.get_chat_member(report_doc["chat_id"], q.from_user.id)
        if member.status not in ("administrator", "creator"):
            return await q.answer("Group admins only.", show_alert=True)
    except Exception:
        return await q.answer("Could not verify your admin status.", show_alert=True)
    await database.reports.update_one({"_id": oid}, {"$set": {"status": "dismissed", "dismissed_by": q.from_user.id, "dismissed_at": datetime.now(timezone.utc)}})
    if q.message:
        await q.message.edit_reply_markup(reply_markup=None)
    await q.answer("Report dismissed.")


@router.message(Command("reports"))
async def list_reports(m: Message):
    if not await require_admin(m, m.bot, "can_delete_messages"):
        return
    rows = await database.reports.find({"chat_id": m.chat.id, "status": "open"}).sort("created_at", -1).limit(20).to_list(20)
    if not rows:
        return await m.reply("There are no open reports.")
    lines = [f"• msg <code>{r['message_id']}</code> — user <code>{r.get('reported_user_id') or 'unknown'}</code> — {r['reason'][:120]}" for r in rows]
    await m.reply("<b>Open reports</b>\n" + "\n".join(lines), parse_mode="HTML")


@router.message(Command("purge"))
async def purge(m: Message):
    if not await require_admin(m, m.bot, "can_delete_messages"):
        return
    if not m.reply_to_message:
        return await m.reply("Reply to the first message and run /purge to delete it and newer messages (up to 100).")
    start, end = m.reply_to_message.message_id, m.message_id
    ids = list(range(start, min(end, start + 100) + 1))
    deleted = 0
    for message_id in ids:
        try:
            await m.bot.delete_message(m.chat.id, message_id)
            deleted += 1
        except Exception:
            pass
    try:
        await m.answer(f"🧹 Deleted {deleted} messages.")
    except Exception:
        pass
