import asyncpg
import redis.asyncio as aioredis
from app.config import settings

_pool = None
_redis = None

async def get_db_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool

async def get_redis():
    global _redis
    if _redis is None:
        url = settings.redis_url
        if not url:
            raise ConnectionError("REDIS_URL not configured")
        # rediss:// (double S) handles TLS automatically — no extra ssl param needed
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis

async def close_connections():
    global _pool, _redis
    if _pool:
        await _pool.close()
        _pool = None
    if _redis:
        await _redis.close()
        _redis = None
