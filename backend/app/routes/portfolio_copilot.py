import logging
from fastapi import APIRouter, Request
from ..use_cases.portfolio_copilot.schemas import PortfolioCopilotInput, PortfolioCopilotFinalOutput
from ..use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
from ..use_cases.portfolio_copilot.services import load_interview_questions
from ..integrations.email.notify import notify_workflow_complete
from ..utils.run_tracker import start_run, record_step, complete_run
from ..auth.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio-copilot", tags=["Portfolio Copilot"])

@router.post("/run", response_model=PortfolioCopilotFinalOutput)
async def run_portfolio_copilot(request: PortfolioCopilotInput, http_request: Request):
    await check_rate_limit(http_request)
    # Start tracking in workflow_runs
    run_id = None
    try:
        run_id = await start_run(
            pipeline_name="portfolio_copilot",
            trigger_type="api",
            metadata={"question_type": getattr(request, 'question_type', 'general')},
        )
    except Exception as e:
        logger.warning("portfolio_copilot: run_tracker start failed: %s", e)

    result = await run_portfolio_copilot_workflow(request)

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
            )
            logger.info("portfolio_copilot: tracked run_id=%s", run_id)
        except Exception as e:
            logger.error("portfolio_copilot: run_tracker complete failed: %s", e, exc_info=True)

    # Email notification
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
