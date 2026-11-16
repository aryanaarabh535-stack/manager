import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import settings
from app.db import init_db, client
from app.routers import core, moderation, community, content, events, admin, security, federation, reports

async def main():
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # Catch-all security moderation is deliberately last so command routers can process commands first.
    dp.include_routers(core.router, admin.router, moderation.router, federation.router, reports.router, community.router, content.router, events.router, security.router)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
