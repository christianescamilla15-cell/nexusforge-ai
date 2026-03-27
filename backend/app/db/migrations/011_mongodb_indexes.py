"""MongoDB index setup for episodic memory.

Run: python -m app.db.migrations.011_mongodb_indexes

Creates:
  - TTL index on expires_at (auto-delete expired episodes)
  - Compound index on (agent_id, created_at) for timeline queries
  - Compound index on (agent_id, episode_type) for type-filtered queries
  - Text index on summary for full-text search
"""

import asyncio
import logging

from app.db.mongo_client import get_mongo_db, close_mongo

logger = logging.getLogger(__name__)

COLLECTION = "agent_episodes"


async def create_indexes():
    """Create all required indexes on the agent_episodes collection."""
    db = await get_mongo_db()
    collection = db[COLLECTION]

    logger.info("Creating MongoDB indexes on '%s'...", COLLECTION)

    await collection.create_index("expires_at", expireAfterSeconds=0)
    logger.info("  - TTL index on expires_at")

    await collection.create_index([("agent_id", 1), ("created_at", -1)])
    logger.info("  - Compound index (agent_id, created_at)")

    await collection.create_index([("agent_id", 1), ("episode_type", 1)])
    logger.info("  - Compound index (agent_id, episode_type)")

    await collection.create_index([("summary", "text")])
    logger.info("  - Text index on summary")

    logger.info("MongoDB indexes created successfully.")
    await close_mongo()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_indexes())
