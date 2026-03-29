"""Portfolio Copilot Workflow — 6-agent pipeline for portfolio intelligence."""
import time, uuid
from .schemas import PortfolioCopilotInput, PortfolioCopilotFinalOutput
from .agents import router_agent, portfolio_rag_agent, project_comparison_agent, skills_mapper_agent, response_formatter_agent, supervisor_agent
from app.metrics.collector import collector

async def run_portfolio_copilot_workflow(request: PortfolioCopilotInput) -> PortfolioCopilotFinalOutput:
    run_id = str(uuid.uuid4())
    start = time.time()
    lang = request.language
    actions, agents_used = [], []

    run = collector.start_run(workflow_name="portfolio_copilot", topology="sequential")
    tid = run.id

    try:
        s1 = collector.start_step(tid, "RouterAgent", 0)
        r1 = await router_agent(request.question, lang)
        collector.end_step(s1)
        agents_used.append("RouterAgent")
        q_type = r1["question_type"]
        actions.append(f"routed: {q_type}")

        s2 = collector.start_step(tid, "PortfolioRAGAgent", 1)
        r2 = await portfolio_rag_agent(request.question, q_type, lang)
        collector.end_step(s2)
        agents_used.append("PortfolioRAGAgent")
        top_projects = r2["top_projects"]
        actions.append(f"retrieved: {r2['results_found']} projects")

        s3 = collector.start_step(tid, "ProjectComparisonAgent", 2)
        r3 = await project_comparison_agent(request.question, top_projects, lang)
        collector.end_step(s3)
        agents_used.append("ProjectComparisonAgent")
        actions.append("compared projects")

        s4 = collector.start_step(tid, "SkillsMapperAgent", 3)
        r4 = await skills_mapper_agent(request.question, top_projects, lang)
        collector.end_step(s4)
        agents_used.append("SkillsMapperAgent")
        actions.append(f"mapped {r4['all_skills_count']} skills")

        s5 = collector.start_step(tid, "ResponseFormatterAgent", 4)
        r5 = await response_formatter_agent(q_type, request.question, top_projects, r3, r4, lang)
        collector.end_step(s5)
        agents_used.append("ResponseFormatterAgent")
        actions.append("formatted response")

        s6 = collector.start_step(tid, "SupervisorAgent", 5)
        r6 = await supervisor_agent(q_type, r5["final_answer"], r2["results_found"], lang)
        collector.end_step(s6, provider=r6.get("provider", ""), tokens=r6.get("total_tokens", 0), cost=r6.get("cost_usd", 0.0))
        agents_used.append("SupervisorAgent")
        actions.append(f"supervisor: {'review' if r6['requires_human_review'] else 'approved'}")

        # Propagate LLM usage from supervisor
        total_tokens = r6.get("total_tokens", 0)
        total_cost = r6.get("cost_usd", 0.0)
        provider_used = r6.get("provider", "none")
        model_used = r6.get("model", "none")
        llm_used = r6.get("llm_used", False)

        collector.end_run(tid)

        return PortfolioCopilotFinalOutput(
            run_id=run_id, status="completed", question_type=q_type,
            recommended_project=r5.get("recommended_project"),
            reasoning=f"Question classified as '{q_type}'. {r2['results_found']} projects retrieved.",
            supporting_projects=r5.get("supporting_projects", []),
            related_skills=r5.get("related_skills", []),
            final_answer=r5["final_answer"],
            requires_human_review=r6["requires_human_review"],
            agents_used=agents_used, actions_taken=actions,
            processing_time_ms=round((time.time() - start) * 1000, 1),
            audit_summary=r6["audit_summary"],
            provider=provider_used,
            model=model_used,
            total_tokens=total_tokens,
            tokens_input=r6.get("tokens_input", 0),
            tokens_output=r6.get("tokens_output", 0),
            cost_usd=total_cost,
            llm_used=llm_used,
        )
    except Exception as e:
        collector.end_run(tid, status="failed")
        return PortfolioCopilotFinalOutput(run_id=run_id, status="error", audit_summary=str(e), agents_used=agents_used, processing_time_ms=round((time.time() - start) * 1000, 1))
