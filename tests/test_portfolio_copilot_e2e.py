"""End-to-end tests for Portfolio Copilot workflow."""
import pytest
import asyncio
from backend.app.use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
from backend.app.use_cases.portfolio_copilot.schemas import PortfolioCopilotInput

class TestPortfolioCopilotE2E:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_best_project_orchestration(self):
        request = PortfolioCopilotInput(
            question="Which project best demonstrates multi-agent orchestration?",
            language="en",
        )
        result = self._run(run_portfolio_copilot_workflow(request))
        assert result.status == "completed"
        assert result.question_type == "best_project"
        assert "NexusForge" in (result.recommended_project or "")
        assert len(result.agents_used) == 6

    def test_comparison_es(self):
        request = PortfolioCopilotInput(
            question="Compara NexusForge y MindScrolling técnicamente",
            language="es",
        )
        result = self._run(run_portfolio_copilot_workflow(request))
        assert result.status == "completed"
        assert result.question_type == "comparison"
        assert len(result.supporting_projects) >= 2

    def test_skills_mapping(self):
        request = PortfolioCopilotInput(
            question="¿Qué habilidades se demuestran en el portafolio?",
            language="es",
        )
        result = self._run(run_portfolio_copilot_workflow(request))
        assert result.status == "completed"
        assert result.question_type == "skills_mapping"
        assert len(result.related_skills) > 0

    def test_product_oriented(self):
        request = PortfolioCopilotInput(
            question="¿Cuál es el proyecto más orientado a producto?",
            language="es",
        )
        result = self._run(run_portfolio_copilot_workflow(request))
        assert result.status == "completed"
        assert result.recommended_project is not None

    def test_general_question(self):
        request = PortfolioCopilotInput(
            question="Hello, tell me something",
            language="en",
        )
        result = self._run(run_portfolio_copilot_workflow(request))
        assert result.status == "completed"

    def test_all_agents_used(self):
        request = PortfolioCopilotInput(question="Best project for RAG?", language="en")
        result = self._run(run_portfolio_copilot_workflow(request))
        assert "RouterAgent" in result.agents_used
        assert "PortfolioRAGAgent" in result.agents_used
        assert "SupervisorAgent" in result.agents_used
