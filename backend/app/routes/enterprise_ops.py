import logging
from fastapi import APIRouter
from ..use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse
from ..use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
from ..integrations.email.notify import notify_workflow_complete
from ..db.client import get_db_pool
from ..db.pipeline_store import save_pipeline_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise-ops", tags=["Enterprise Operations"])

@router.post("/process", response_model=OperationsResponse)
async def process_operations_request(request: OperationsRequest):
    """Process an enterprise operations request through the 8-agent workflow."""
    result = await run_enterprise_ops_workflow(request)

    # Persist to DB
    try:
        pool = await get_db_pool()
        logger.info("enterprise_ops: pool=%s, status=%s, tokens=%s", pool is not None, result.status, result.total_tokens)
        if pool:
            run_id = await save_pipeline_run(
                pool,
                pipeline_name="enterprise_operations",
                status=result.status,
                trigger_source="backend",
                total_tokens=result.total_tokens or 0,
                cost_usd=float(result.cost_usd or 0.0),
                processing_time_ms=int(result.processing_time_ms or 0),
                llm_used=bool(result.llm_used),
                agents_used=result.agents_used or [],
                steps=result.actions_taken or [],
            )
            logger.info("enterprise_ops: persisted run_id=%s", run_id)
        else:
            logger.warning("enterprise_ops: no DB pool available")
    except Exception as e:
        logger.error("enterprise_ops: PERSIST FAILED: %s", e, exc_info=True)

    # Email notification
    await notify_workflow_complete(
        workflow_name="Enterprise Operations",
        status=result.status,
        summary=result.response_message,
        agents_used=result.agents_used,
        total_tokens=result.total_tokens or 0,
        cost_usd=result.cost_usd or 0.0,
        processing_time_ms=result.processing_time_ms or 0,
        extra_details={"intent": result.intent, "customer": result.customer_name or "N/A"},
    )

    return result

@router.get("/health")
async def enterprise_ops_health():
    """Health check for the Enterprise Operations use case."""
    return {
        "status": "operational",
        "agents": [
            "IntakeAgent", "IntentClassifierAgent", "CustomerContextAgent",
            "DocumentRAGAgent", "SchedulerAgent", "CRMUpdateAgent",
            "NotificationAgent", "SupervisorAgent",
        ],
        "intents_supported": [
            "reschedule_meeting", "verify_contract", "check_onboarding",
            "consult_policy", "update_crm", "general_inquiry",
        ],
    }
