from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message


async def require_admin(message: Message, bot: Bot, permission: str = "can_restrict_members") -> bool:
    if not message.from_user:
        return False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        await message.reply("I could not verify your administrator status. Please try again.")
        return False
    if member.status == ChatMemberStatus.CREATOR:
        return True
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        await message.reply("You need to be a group administrator to use this command.")
        return False
    if permission and not getattr(member, permission, False):
        await message.reply(f"You need the Telegram permission `{permission}` to use this command.")
        return False
    return True


async def target_user(message: Message, argument: str | None = None) -> int | None:
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    if argument:
        raw = argument.strip()
        if raw.lstrip("-").isdigit():
            return int(raw)
    return None
