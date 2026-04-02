from fastapi import APIRouter
from ..use_cases.portfolio_copilot.schemas import PortfolioCopilotInput, PortfolioCopilotFinalOutput
from ..use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
from ..use_cases.portfolio_copilot.services import load_interview_questions
from ..integrations.email.notify import notify_workflow_complete

router = APIRouter(prefix="/portfolio-copilot", tags=["Portfolio Copilot"])

@router.post("/run", response_model=PortfolioCopilotFinalOutput)
async def run_portfolio_copilot(request: PortfolioCopilotInput):
    result = await run_portfolio_copilot_workflow(request)

    await notify_workflow_complete(
        workflow_name="Portfolio Copilot",
        status=result.status,
        summary=result.final_answer or result.reasoning or "Analysis complete",
        agents_used=result.agents_used or [],
        total_tokens=result.total_tokens or 0,
        cost_usd=result.cost_usd or 0.0,
        processing_time_ms=result.processing_time_ms or 0,
        extra_details={"project": result.recommended_project or "N/A", "type": result.question_type},
    )

    return result

@router.get("/examples")
async def get_example_questions():
    questions = load_interview_questions()
    return {"questions": questions, "total": len(questions)}

@router.get("/health")
async def portfolio_copilot_health():
    return {
        "status": "operational",
        "agents": ["RouterAgent", "PortfolioRAGAgent", "ProjectComparisonAgent", "SkillsMapperAgent", "ResponseFormatterAgent", "SupervisorAgent"],
        "question_types": ["best_project", "comparison", "skills_mapping", "technical_deep_dive", "general"],
        "projects_indexed": 7,
    }
