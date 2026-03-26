import json
import logging
from uuid import UUID

from app.db.client import get_redis

logger = logging.getLogger(__name__)


async def enqueue_task(stream: str, task_data: dict) -> str:
    """Push a task to a Redis Stream using XADD.

    Returns the message ID assigned by Redis.
    """
    redis = await get_redis()
    payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in task_data.items()}
    message_id = await redis.xadd(stream, payload)
    logger.info("Enqueued task to %s: %s", stream, message_id)
    return message_id


async def enqueue_workflow_run(run_id: UUID, workflow_id: UUID) -> str:
    """Push a workflow execution task to the workflows stream."""
    return await enqueue_task(
        "stream:workflows",
        {
            "run_id": str(run_id),
            "workflow_id": str(workflow_id),
            "action": "execute",
        },
    )
