"""Extended agent tests — verifies all 24 agents registered in Session 3."""

import importlib
import pytest
from app.agents.registry import list_agents, get_agent
from app.agents.base import BaseAgent, AgentResult


EXPECTED_AGENT_COUNT = 22  # Core agents from app/agents/

EXPECTED_AGENTS = [
    "classifier", "extractor", "summarizer", "analyzer",
    "enricher", "validator", "reporter", "repair",
    "normalizer", "researcher", "translator", "compliance",
    "monitor", "router_agent", "critic", "planner",
    "knowledge", "scraper", "ocr", "sentiment",
    "scheduler", "webhook",
]

# Additional agents registered by swarm modules (judge from consensus, router from adaptive)
SWARM_EXTRA_AGENTS = ["judge", "router"]


def _ensure_all_agents_registered():
    """Ensure all agent modules are imported, triggering registration."""
    from app.agents import registry
    if len(registry._registry) < EXPECTED_AGENT_COUNT:
        from app.agents import (
            classifier, extractor, summarizer, analyzer,
            enricher, validator, reporter, repair,
            normalizer, researcher, translator, compliance,
            monitor, router, critic, planner,
            knowledge, scraper, ocr, sentiment,
            scheduler, webhook,
        )
        all_mods = [
            classifier, extractor, summarizer, analyzer,
            enricher, validator, reporter, repair,
            normalizer, researcher, translator, compliance,
            monitor, router, critic, planner,
            knowledge, scraper, ocr, sentiment,
            scheduler, webhook,
        ]
        for mod in all_mods:
            importlib.reload(mod)


@pytest.fixture(autouse=True)
def register_all_agents():
    """Ensure all 24 agents are registered before each test."""
    _ensure_all_agents_registered()


class TestAgentRegistryCount:
    """Verify all 22 core agents are registered."""

    def test_agent_count_at_least_22(self):
        agents = list_agents()
        assert len(agents) >= EXPECTED_AGENT_COUNT, (
            f"Expected at least {EXPECTED_AGENT_COUNT} agents, got {len(agents)}: {agents}"
        )

    def test_all_core_agents_present(self):
        agents = set(list_agents())
        for expected in EXPECTED_AGENTS:
            assert expected in agents, f"Missing core agent: {expected}"


class TestAllAgentsHaveMetadata:
    """Each agent instance must have name, description, agent_type."""

    @pytest.mark.parametrize("agent_type", EXPECTED_AGENTS)
    def test_agent_has_name(self, agent_type):
        agent = get_agent(agent_type)
        assert hasattr(agent, "name")
        assert isinstance(agent.name, str)
        assert len(agent.name) > 0

    @pytest.mark.parametrize("agent_type", EXPECTED_AGENTS)
    def test_agent_has_description(self, agent_type):
        agent = get_agent(agent_type)
        assert hasattr(agent, "description")
        assert isinstance(agent.description, str)
        assert len(agent.description) > 0

    @pytest.mark.parametrize("agent_type", EXPECTED_AGENTS)
    def test_agent_has_agent_type(self, agent_type):
        agent = get_agent(agent_type)
        assert hasattr(agent, "agent_type")
        assert isinstance(agent.agent_type, str)


class TestNewAgentsExist:
    """Verify Session 3 agents are in the registry."""

    def test_normalizer_registered(self):
        assert "normalizer" in list_agents()

    def test_researcher_registered(self):
        assert "researcher" in list_agents()

    def test_translator_registered(self):
        assert "translator" in list_agents()

    def test_compliance_registered(self):
        assert "compliance" in list_agents()

    def test_monitor_registered(self):
        assert "monitor" in list_agents()

    def test_router_agent_registered(self):
        assert "router_agent" in list_agents()

    def test_critic_registered(self):
        assert "critic" in list_agents()

    def test_planner_registered(self):
        assert "planner" in list_agents()

    def test_knowledge_registered(self):
        assert "knowledge" in list_agents()

    def test_scraper_registered(self):
        assert "scraper" in list_agents()

    def test_ocr_registered(self):
        assert "ocr" in list_agents()

    def test_sentiment_registered(self):
        assert "sentiment" in list_agents()

    def test_scheduler_registered(self):
        assert "scheduler" in list_agents()

    def test_webhook_registered(self):
        assert "webhook" in list_agents()


class TestDemoModeExecution:
    """Agents should return valid results in demo mode (no LLM)."""

    @pytest.mark.asyncio
    async def test_sentiment_demo(self):
        agent = get_agent("sentiment")
        result = await agent.execute({"text": "Great product"}, {"demo": True})
        assert isinstance(result, AgentResult)
        assert "sentiment" in result.output
        assert result.output["sentiment"] in ("positive", "negative", "neutral")
        assert "score" in result.output

    @pytest.mark.asyncio
    async def test_planner_demo(self):
        agent = get_agent("planner")
        result = await agent.execute({"task": "Process invoices"}, {"demo": True})
        assert isinstance(result, AgentResult)
        assert "plan" in result.output
        assert isinstance(result.output["plan"], list)
        assert "estimated_steps" in result.output

    @pytest.mark.asyncio
    async def test_classifier_demo(self):
        agent = get_agent("classifier")
        result = await agent.execute({"text": "Legal contract"}, {"demo": True})
        assert isinstance(result, AgentResult)
        assert "category" in result.output

    @pytest.mark.asyncio
    async def test_summarizer_demo(self):
        agent = get_agent("summarizer")
        result = await agent.execute({"text": "A long document..."}, {"demo": True})
        assert isinstance(result, AgentResult)
        assert "summary" in result.output
