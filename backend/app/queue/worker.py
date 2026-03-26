import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from app.db.client import get_redis

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]


async def _ensure_group(redis, stream: str, group: str) -> None:
    """Create the consumer group if it doesn't already exist."""
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        # Group already exists
        pass


async def start_worker(
    stream: str,
    handler: Handler,
    group: str = "workers",
    consumer: str = "worker-1",
    batch_size: int = 10,
    block_ms: int = 5000,
) -> None:
    """Consume messages from a Redis Stream, process, and acknowledge.

    Designed to run as a background task inside FastAPI lifespan.
    """
    redis = await get_redis()
    await _ensure_group(redis, stream, group)

    logger.info("Worker started: stream=%s group=%s consumer=%s", stream, group, consumer)

    while True:
        try:
            messages = await redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=batch_size,
                block=block_ms,
            )

            if not messages:
                continue

            for _stream_name, entries in messages:
                for message_id, fields in entries:
                    try:
                        # Decode JSON values back into Python objects
                        parsed = {}
                        for k, v in fields.items():
                            try:
                                parsed[k] = json.loads(v)
                            except (json.JSONDecodeError, TypeError):
                                parsed[k] = v

                        logger.info("Processing %s from %s", message_id, stream)
                        await handler(parsed)
                        await redis.xack(stream, group, message_id)
                        logger.info("Acknowledged %s", message_id)

                    except Exception:
                        logger.exception("Failed to process message %s", message_id)
                        # Message stays in PEL for retry / dead-letter handling

        except asyncio.CancelledError:
            logger.info("Worker shutting down: stream=%s", stream)
            break
        except Exception:
            logger.exception("Worker error on stream %s, retrying in 2s", stream)
            await asyncio.sleep(2)
