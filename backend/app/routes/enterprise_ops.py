import logging
from fastapi import APIRouter
from ..use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse
from ..use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
from ..integrations.email.notify import notify_workflow_complete
from ..db.client import get_db_pool
from ..db.pipeline_store import save_pipeline_run
from ..utils.run_tracker import start_run, record_step, complete_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise-ops", tags=["Enterprise Operations"])

@router.post("/process", response_model=OperationsResponse)
async def process_operations_request(request: OperationsRequest):
    """Process an enterprise operations request through the 8-agent workflow."""
    # Track in workflow_runs for Executions page
    tracker_run_id = None
    try:
        tracker_run_id = await start_run(
            "Enterprise Ops Pipeline",
            trigger_type="manual",
            metadata={"input": request.message[:200] if request.message else ""},
        )
    except Exception as e:
        logger.warning("enterprise_ops: run_tracker start failed: %s", e)

    result = await run_enterprise_ops_workflow(request)

    # Record each agent as a step
    if tracker_run_id:
        try:
            agents = result.agents_used or []
            per_agent_tokens = (result.total_tokens or 0) // max(len(agents), 1)
            per_agent_cost = float(result.cost_usd or 0) / max(len(agents), 1)
            per_agent_ms = int(result.processing_time_ms or 0) // max(len(agents), 1)
            for agent_name in agents:
                await record_step(
                    tracker_run_id, agent_name, agent_name.lower().replace("agent", ""),
                    status="completed",
                    tokens_used=per_agent_tokens,
                    cost_usd=per_agent_cost,
                    duration_ms=per_agent_ms,
                )
            await complete_run(
                tracker_run_id,
                status=result.status or "completed",
                total_tokens=result.total_tokens or 0,
                total_cost_usd=float(result.cost_usd or 0),
            )
        except Exception as e:
            logger.warning("enterprise_ops: run_tracker complete failed: %s", e)

    # Persist to pipeline_runs (legacy)
    try:
        pool = await get_db_pool()
        if pool:
            await save_pipeline_run(
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
