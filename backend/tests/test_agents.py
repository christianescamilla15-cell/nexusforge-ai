"""Tests for agent registry and agent execution (mocked LLM)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _import_agents():
    """Import agents module to trigger self-registration."""
    # Reset registry for clean tests
    from app.agents import registry
    registry._registry.clear()

    # Re-import agent modules to trigger register_agent() calls.
    # We need to mock the LLM router since it's imported at module level.
    import importlib
    from app.agents import classifier, extractor, summarizer, analyzer, enricher, validator, reporter, repair
    for mod in [classifier, extractor, summarizer, analyzer, enricher, validator, reporter, repair]:
        importlib.reload(mod)


@pytest.fixture(autouse=True)
def register_all_agents():
    """Ensure all agents are registered before each test."""
    _import_agents()


def test_all_eight_agents_registered():
    from app.agents.registry import list_agents
    agents = list_agents()
    assert len(agents) == 8


def test_list_agents_returns_all_types():
    from app.agents.registry import list_agents
    agents = list_agents()
    expected = {"classifier", "extractor", "summarizer", "analyzer", "enricher", "validator", "reporter", "repair"}
    assert set(agents) == expected


def test_get_agent_returns_correct_agent():
    from app.agents.registry import get_agent
    agent = get_agent("classifier")
    assert agent.agent_type == "classifier"


def test_get_agent_unknown_type_raises():
    from app.agents.registry import get_agent
    with pytest.raises(ValueError, match="Unknown agent type"):
        get_agent("nonexistent_agent")


def test_each_agent_has_name_and_description():
    from app.agents.registry import list_agents, get_agent
    for agent_type in list_agents():
        agent = get_agent(agent_type)
        assert hasattr(agent, "name") and agent.name
        assert hasattr(agent, "description") and agent.description


@pytest.mark.asyncio
async def test_classifier_execute_demo_mode():
    from app.agents.registry import get_agent
    agent = get_agent("classifier")
    result = await agent.execute({"text": "test"}, config={"demo": True})
    assert "category" in result.output
    assert "confidence" in result.output


@pytest.mark.asyncio
async def test_validator_execute_demo_mode():
    from app.agents.registry import get_agent
    agent = get_agent("validator")
    result = await agent.execute({"output": {"key": "value"}}, config={"demo": True})
    assert "score" in result.output
    assert 0 <= result.output["score"] <= 100


@pytest.mark.asyncio
async def test_repair_execute_demo_mode():
    from app.agents.registry import get_agent
    agent = get_agent("repair")
    result = await agent.execute(
        {"error": "timeout", "step_name": "s1", "step_type": "classifier"},
        config={"demo": True},
    )
    assert "diagnosis" in result.output
    assert "fix_type" in result.output


@pytest.mark.asyncio
async def test_classifier_fallback_without_llm():
    """Classifier should gracefully fall back when LLM is unavailable."""
    from app.agents.registry import get_agent
    agent = get_agent("classifier")
    # Execute without demo flag; LLM is not available, so it should hit fallback
    result = await agent.execute({"text": "This is a financial report about Q3 earnings."})
    assert result.output["category"] in ["general", "financial", "legal", "technical", "medical"]
    assert result.provider in ("local", "fallback", "groq", "claude")


def test_agent_result_has_required_fields():
    from app.agents.base import AgentResult
    result = AgentResult(output={"test": True})
    assert result.tokens_used == 0
    assert result.cost_usd == 0.0
    assert result.provider == "local"
    assert result.model == "none"
