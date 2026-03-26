import logging
from dataclasses import dataclass

from app.db.client import get_db_pool
from app.rag.embeddings import get_embedding

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict
    similarity: float


async def search(query: str, top_k: int = 5) -> list[ChunkResult]:
    """Embed query and call match_chunks to find semantically similar chunks."""
    embedding = await get_embedding(query)
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM match_chunks($1::vector, $2)",
            embedding_str,
            top_k,
        )

    results = []
    for row in rows:
        results.append(
            ChunkResult(
                id=str(row["id"]),
                document_id=str(row["document_id"]),
                content=row["content"],
                chunk_index=row["chunk_index"],
                metadata=row["metadata"] or {},
                similarity=row["similarity"],
            )
        )

    logger.info("RAG search for '%s': %d results", query[:60], len(results))
    return results


async def search_with_context(query: str, top_k: int = 5) -> str:
    """Search and build a context string suitable for LLM consumption."""
    results = await search(query, top_k=top_k)

    if not results:
        return "No relevant documents found."

    context_parts = []
    for i, r in enumerate(results, 1):
        title = r.metadata.get("title", f"Document {r.document_id[:8]}")
        context_parts.append(
            f"[{i}] {title} (similarity: {r.similarity:.3f})\n{r.content}"
        )

    return "\n\n---\n\n".join(context_parts)
