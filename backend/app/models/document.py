from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class DocumentUpload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    file_type: Optional[str] = "text"
    language: str = "en"
    metadata: dict = {}

class DocumentSearch(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)

class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    similarity: float
    metadata: dict

class DocumentResponse(BaseModel):
    id: UUID
    title: str
    content: str
    file_type: Optional[str]
    language: str
    status: str
    created_at: datetime
