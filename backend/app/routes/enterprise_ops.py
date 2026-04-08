import logging
from fastapi import APIRouter, HTTPException, Request
from ..auth.jwt_handler import verify_token
from ..use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse
from ..use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
from ..integrations.email.notify import notify_workflow_complete
from ..utils.run_tracker import start_run, record_step, complete_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise-ops", tags=["Enterprise Operations"])


def _get_user_id(req: Request) -> str:
    """Extract and verify user from JWT. Raises 401 if missing/invalid."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data["sub"]


@router.post("/process", response_model=OperationsResponse)
async def process_operations_request(request: OperationsRequest, req: Request):
    """Process an enterprise operations request through the 8-agent workflow."""
    user_id = _get_user_id(req)

    # Start tracking in workflow_runs
    tracker_run_id = None
    try:
        tracker_run_id = await start_run(
            pipeline_name="enterprise_operations",
            trigger_type="api",
            user_id=user_id,
            metadata={"input": request.message[:200] if request.message else ""},
        )
    except Exception as e:
        logger.warning("enterprise_ops: run_tracker start failed: %s", e)

    result = await run_enterprise_ops_workflow(request)

    # Record each agent as a step and complete the run
    if tracker_run_id:
        try:
            agents = result.agents_used or []
            agent_count = max(len(agents), 1)
            per_agent_tokens = (result.total_tokens or 0) // agent_count
            per_agent_cost = float(result.cost_usd or 0) / agent_count
            per_agent_ms = int(result.processing_time_ms or 0) // agent_count
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
                agents_used=result.agents_used or [],
            )
        except Exception as e:
            logger.warning("enterprise_ops: run_tracker complete failed: %s", e)

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
