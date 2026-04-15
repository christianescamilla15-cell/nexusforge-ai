import logging
from fastapi import APIRouter, Request
from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput, DocumentIntelligenceFinalOutput
from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
from ..use_cases.document_intelligence.services import load_sample_documents
from ..integrations.email.notify import notify_workflow_complete
from ..utils.run_tracker import start_run, record_step, complete_run
from ..auth.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document-intelligence", tags=["Document Intelligence"])

@router.post("/run", response_model=DocumentIntelligenceFinalOutput)
async def run_document_workflow(request: DocumentIntelligenceInput, http_request: Request):
    await check_rate_limit(http_request)
    # Start tracking in workflow_runs
    run_id = None
    try:
        run_id = await start_run(
            pipeline_name="document_intelligence",
            trigger_type="api",
            metadata={"filename": request.filename or "unknown"},
        )
    except Exception as e:
        logger.warning("doc_intel: run_tracker start failed: %s", e)

    result = await run_document_intelligence_workflow(request)

    # Record steps and complete the run
    if run_id:
        try:
            agents = result.agents_used or []
            agent_count = max(len(agents), 1)
            per_agent_tokens = (result.total_tokens or 0) // agent_count
            per_agent_cost = float(result.cost_usd or 0) / agent_count
            per_agent_ms = int(result.processing_time_ms or 0) // agent_count
            for agent_name in agents:
                await record_step(
                    run_id, agent_name, agent_name.lower().replace("agent", ""),
                    status="completed",
                    tokens_used=per_agent_tokens,
                    cost_usd=per_agent_cost,
                    duration_ms=per_agent_ms,
                )
            await complete_run(
                run_id,
                status=result.status or "completed",
                total_tokens=result.total_tokens or 0,
                total_cost_usd=float(result.cost_usd or 0),
                agents_used=result.agents_used or [],
                extra_metadata={"document_type": result.document_type},
            )
            logger.info("doc_intel: tracked run_id=%s", run_id)
        except Exception as e:
            logger.error("doc_intel: run_tracker complete failed: %s", e, exc_info=True)

    # Email notification
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
