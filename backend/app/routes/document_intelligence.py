from fastapi import APIRouter
from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput, DocumentIntelligenceFinalOutput
from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
from ..use_cases.document_intelligence.services import load_sample_documents
from ..integrations.email.notify import notify_workflow_complete

router = APIRouter(prefix="/document-intelligence", tags=["Document Intelligence"])

@router.post("/run", response_model=DocumentIntelligenceFinalOutput)
async def run_document_workflow(request: DocumentIntelligenceInput):
    result = await run_document_intelligence_workflow(request)

    await notify_workflow_complete(
        workflow_name="Document Intelligence",
        status=result.status,
        summary=result.summary or "Document processed",
        agents_used=result.agents_used or [],
        total_tokens=result.total_tokens or 0,
        cost_usd=result.cost_usd or 0.0,
        processing_time_ms=result.processing_time_ms or 0,
        extra_details={"document_type": result.document_type or "unknown"},
    )

    return result

@router.get("/examples")
async def get_example_documents():
    docs = load_sample_documents()
    return {"documents": [{"id": d["id"], "filename": d["filename"], "type": d["type"], "language": d["language"], "preview": d["content"][:100] + "..."} for d in docs], "total": len(docs)}

@router.get("/health")
async def document_intelligence_health():
    return {
        "status": "operational",
        "agents": ["DocumentIngestionAgent", "DocumentClassifierAgent", "SchemaExtractionAgent", "ValidationAgent", "SummaryAgent", "StorageAgent", "SupervisorAgent"],
        "supported_types": ["contract", "policy", "invoice", "resume", "report"],
    }
