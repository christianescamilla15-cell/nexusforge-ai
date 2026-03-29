from fastapi import APIRouter
from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput, DocumentIntelligenceFinalOutput
from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
from ..use_cases.document_intelligence.services import load_sample_documents

router = APIRouter(prefix="/document-intelligence", tags=["Document Intelligence"])

@router.post("/run", response_model=DocumentIntelligenceFinalOutput)
async def run_document_workflow(request: DocumentIntelligenceInput):
    return await run_document_intelligence_workflow(request)

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
