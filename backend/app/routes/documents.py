"""Document upload, listing, and semantic search routes."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db.client import get_db_pool
from app.models.document import DocumentUpload, DocumentSearch, DocumentResponse, ChunkResponse
from app.rag.indexer import index_document
from app.rag.retriever import search

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=201, response_model=DocumentResponse)
async def upload_document(body: DocumentUpload):
    """Upload a document and index it for RAG retrieval."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO documents (title, content, file_type, language, metadata, status)
                   VALUES ($1, $2, $3, $4, $5::jsonb, 'pending')
                   RETURNING id, title, content, file_type, language, status, created_at""",
                body.title,
                body.content,
                body.file_type,
                body.language,
                json.dumps(body.metadata),
            )

        doc_id = row["id"]

        # Index document asynchronously (chunking + embedding)
        try:
            await index_document(doc_id, body.content)
        except Exception as exc:
            logger.warning("Indexing failed for document %s: %s", doc_id, exc)
            # Document is still saved; indexing can be retried later

        return DocumentResponse(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            file_type=row["file_type"],
            language=row["language"],
            status="indexed",
            created_at=row["created_at"],
        )
    except Exception as exc:
        logger.exception("Failed to upload document")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """List all documents with pagination."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, title, content, file_type, language, status, created_at
                   FROM documents
                   ORDER BY created_at DESC
                   OFFSET $1 LIMIT $2""",
                skip,
                limit,
            )
        return [
            DocumentResponse(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                file_type=r["file_type"],
                language=r["language"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    except Exception as exc:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search", response_model=list[ChunkResponse])
async def search_documents(body: DocumentSearch):
    """Semantic search across indexed documents."""
    try:
        results = await search(body.query, top_k=body.top_k)
        return [
            ChunkResponse(
                id=r.id,
                document_id=r.document_id,
                content=r.content,
                chunk_index=r.chunk_index,
                similarity=r.similarity,
                metadata=r.metadata,
            )
            for r in results
        ]
    except Exception as exc:
        logger.exception("Document search failed")
        raise HTTPException(status_code=500, detail=str(exc))
