from fastapi import APIRouter
from ..use_cases.enterprise_ops.schemas import OperationsRequest, OperationsResponse
from ..use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow

router = APIRouter(prefix="/enterprise-ops", tags=["Enterprise Operations"])

@router.post("/process", response_model=OperationsResponse)
async def process_operations_request(request: OperationsRequest):
    """Process an enterprise operations request through the 8-agent workflow."""
    return await run_enterprise_ops_workflow(request)

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
