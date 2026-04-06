"""Semantic memory — pgvector-backed long-term knowledge store."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.db.client import get_db_pool
from app.rag.embeddings import get_embedding

logger = logging.getLogger(__name__)


class SemanticMemory:
    """Tier-3 memory: stores embedded text vectors in PostgreSQL (pgvector)
    for similarity-based retrieval of past agent experiences."""

    # --- store ---

    async def store(
        self,
        agent_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Embed *text* with Voyage AI and persist in document_chunks."""
        try:
            embedding = await get_embedding(text)
            meta = metadata or {}
            meta.update({"agent_id": agent_id, "memory_type": "semantic", "stored_at": time.time()})
            # Build pgvector-compatible string: "[0.1,0.2,...]" and cast to ::vector
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            pool = await get_db_pool()
            await pool.execute(
                """
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding, metadata)
                VALUES (gen_random_uuid(), 0, $1, $2::vector, $3)
                """,
                text,
                embedding_str,
                json.dumps(meta),
            )
            return True
        except Exception as exc:
            logger.warning("SemanticMemory.store failed: %s", exc)
            return False

    # --- recall ---

    async def recall(
        self,
        agent_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Semantic search for similar past experiences."""
        try:
            query_embedding = await get_embedding(query)
            query_embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
            pool = await get_db_pool()
            rows = await pool.fetch(
                """
                SELECT content,
                       metadata,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM   document_chunks
                WHERE  metadata::jsonb @> $2::jsonb
                ORDER  BY embedding <=> $1::vector
                LIMIT  $3
                """,
                query_embedding_str,
                json.dumps({"agent_id": agent_id, "memory_type": "semantic"}),
                top_k,
            )
            return [
                {
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "similarity": float(row["similarity"]),
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("SemanticMemory.recall failed: %s", exc)
            return []

    # --- cross-agent knowledge transfer ---

    async def share_knowledge(
        self,
        from_agent: str,
        to_agent: str,
        text: str,
    ) -> bool:
        """Store knowledge tagged for *to_agent* originating from *from_agent*."""
        return await self.store(
            agent_id=to_agent,
            text=text,
            metadata={"shared_from": from_agent},
        )
