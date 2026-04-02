from fastapi import APIRouter
from ..use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse
from ..use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
from ..integrations.email.notify import notify_workflow_complete

router = APIRouter(prefix="/enterprise-ops", tags=["Enterprise Operations"])

@router.post("/process", response_model=OperationsResponse)
async def process_operations_request(request: OperationsRequest):
    """Process an enterprise operations request through the 8-agent workflow."""
    result = await run_enterprise_ops_workflow(request)

    # Fire-and-forget email notification
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
