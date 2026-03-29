from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DocumentIntelligenceInput(BaseModel):
    content: str = Field(..., description="Document text content")
    filename: Optional[str] = None
    language: str = Field(default="es")
    document_type_hint: Optional[str] = None

class DocumentClassificationOutput(BaseModel):
    document_type: str  # contract, policy, invoice, resume, report, unknown
    confidence: float
    language_detected: str

class ExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float = 1.0

class SchemaExtractionOutput(BaseModel):
    document_type: str
    fields: List[ExtractedField]
    raw_extraction: Dict[str, Any] = {}

class ValidationError(BaseModel):
    field: str
    error: str
    severity: str = "warning"  # warning, error, critical

class ValidationOutput(BaseModel):
    schema_valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []

class SummaryOutput(BaseModel):
    summary: str
    key_points: List[str] = []
    word_count: int = 0

class DocumentIntelligenceFinalOutput(BaseModel):
    run_id: str
    status: str
    document_type: str
    extracted_fields: Dict[str, Any] = {}
    schema_valid: bool = False
    validation_errors: List[Dict[str, str]] = []
    summary: str = ""
    key_points: List[str] = []
    requires_human_review: bool = False
    agents_used: List[str] = []
    actions_taken: List[str] = []
    processing_time_ms: Optional[float] = None
    audit_summary: str = ""
