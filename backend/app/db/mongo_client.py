"""MongoDB async client for polyglot persistence."""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client = None
_db = None


async def get_mongo_db():
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
        _db = _client[settings.mongodb_db]
    return _db


async def close_mongo():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
