import logging
from uuid import UUID

from app.db.client import get_db_pool
from app.rag.embeddings import get_embeddings_batch

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


async def index_document(document_id: UUID, content: str) -> int:
    """Chunk text, embed with Voyage AI, and store in document_chunks table.

    Returns the number of chunks indexed.
    """
    pool = await get_db_pool()

    chunks = chunk_text(content)
    if not chunks:
        logger.warning("No chunks produced for document %s", document_id)
        return 0

    logger.info("Indexing document %s: %d chunks", document_id, len(chunks))

    # Embed all chunks in batch
    embeddings = await get_embeddings_batch(chunks)

    # Insert chunks with embeddings into pgvector
    async with pool.acquire() as conn:
        async with conn.transaction():
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                token_count = len(chunk.split())
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                await conn.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, content, token_count, embedding)
                    VALUES ($1, $2, $3, $4, $5::vector)
                    """,
                    document_id,
                    idx,
                    chunk,
                    token_count,
                    embedding_str,
                )

            # Mark document as indexed
            await conn.execute(
                "UPDATE documents SET status = 'indexed' WHERE id = $1",
                document_id,
            )

    logger.info("Document %s indexed successfully (%d chunks)", document_id, len(chunks))
    return len(chunks)
