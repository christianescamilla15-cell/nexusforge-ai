from fastapi import APIRouter
from ..use_cases.portfolio_copilot.schemas import PortfolioCopilotInput, PortfolioCopilotFinalOutput
from ..use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
from ..use_cases.portfolio_copilot.services import load_interview_questions

router = APIRouter(prefix="/portfolio-copilot", tags=["Portfolio Copilot"])

@router.post("/run", response_model=PortfolioCopilotFinalOutput)
async def run_portfolio_copilot(request: PortfolioCopilotInput):
    return await run_portfolio_copilot_workflow(request)

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
