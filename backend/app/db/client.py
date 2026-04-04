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
        import ssl as _ssl
        url = settings.redis_url
        if not url:
            raise ConnectionError("REDIS_URL not configured")
        # Upstash requires TLS — rediss:// URLs need ssl context
        if url.startswith("rediss://"):
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            _redis = aioredis.from_url(url, decode_responses=True, ssl=ctx)
        else:
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
