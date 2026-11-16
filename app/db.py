from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.database_url)
database = client[settings.mongo_database]

async def init_db() -> None:
    # Indexes provide the uniqueness and lookup behavior previously supplied by SQL constraints.
    await database.chat_settings.create_index("chat_id", unique=True)
    await database.warnings.create_index([("chat_id", 1), ("user_id", 1), ("created_at", -1)])
    await database.saved_items.create_index([("chat_id", 1), ("kind", 1), ("trigger", 1)], unique=True)
    await database.blocklist_entries.create_index([("chat_id", 1), ("phrase", 1)], unique=True)
    await database.approved_users.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
    await database.federations.create_index("public_id", unique=True)
    await database.federation_chats.create_index("chat_id", unique=True)
    await database.flood_events.create_index("created_at", expireAfterSeconds=60)
    await database.raid_events.create_index("created_at", expireAfterSeconds=60)
    await database.federation_bans.create_index([("federation_id", 1), ("user_id", 1)], unique=True)
    await database.admin_cache.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
    await database.captcha_pending.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
    await database.captcha_pending.create_index("expires_at", expireAfterSeconds=0)
    await database.reports.create_index([("chat_id", 1), ("created_at", -1)])
