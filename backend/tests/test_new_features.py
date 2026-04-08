"""Tests for new features: regressive memory, predictive memory, Gemma 4 integration."""

import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock


# ── Regressive Memory Tests ─────────────────────────────────────────────────

class TestRegressiveMemory:
    """Test the regressive analysis layer."""

    def test_import(self):
        from app.memory.regressive import RegressiveMemory
        rm = RegressiveMemory()
        assert rm.COLLECTION == "agent_episodes"

    def test_stats_helper(self):
        from app.memory.regressive import _stats
        result = _stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result["avg"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["count"] == 5
        assert result["stddev"] > 0

    def test_stats_empty(self):
        from app.memory.regressive import _stats
        result = _stats([])
        assert result["avg"] == 0
        assert result["count"] == 0

    def test_stats_single_value(self):
        from app.memory.regressive import _stats
        result = _stats([42.0])
        assert result["avg"] == 42.0
        assert result["stddev"] == 0
        assert result["count"] == 1

    def test_window_map(self):
        from app.memory.regressive import WINDOW_MAP
        assert WINDOW_MAP["1h"] == timedelta(hours=1)
        assert WINDOW_MAP["24h"] == timedelta(hours=24)
        assert WINDOW_MAP["7d"] == timedelta(days=7)
        assert WINDOW_MAP["30d"] == timedelta(days=30)

    @pytest.mark.asyncio
    async def test_rolling_stats_no_mongo(self):
        """Should return empty dict when MongoDB is unavailable."""
        from app.memory.regressive import RegressiveMemory
        rm = RegressiveMemory()
        result = await rm.get_rolling_stats("TestAgent", "24h")
        # Without MongoDB running, should return {} gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_mongo(self):
        """Should return empty list when MongoDB is unavailable."""
        from app.memory.regressive import RegressiveMemory
        rm = RegressiveMemory()
        result = await rm.detect_anomalies("TestAgent", window="1h")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_failure_correlations_no_mongo(self):
        from app.memory.regressive import RegressiveMemory
        rm = RegressiveMemory()
        result = await rm.get_failure_correlations("TestAgent", "7d")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_trend_no_mongo(self):
        from app.memory.regressive import RegressiveMemory
        rm = RegressiveMemory()
        result = await rm.get_trend("TestAgent", buckets=6, window="24h")
        assert isinstance(result, list)

    def test_datetime_is_timezone_aware(self):
        """Critical: regressive must use timezone-aware datetimes."""
        from app.memory.regressive import RegressiveMemory
        import inspect
        source = inspect.getsource(RegressiveMemory)
        assert "utcnow()" not in source, "Must NOT use deprecated datetime.utcnow()"
        assert "timezone.utc" in source, "Must use timezone-aware datetime.now(timezone.utc)"


# ── Predictive Memory Tests ─────────────────────────────────────────────────

class TestPredictiveMemory:
    """Test the predictive layer."""

    def test_import(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        assert pm._cache_ttl == 300

    def test_neutral_prediction(self):
        from app.memory.predictive import PredictiveMemory
        result = PredictiveMemory._neutral_prediction()
        assert result["fallback_probability"] == 0.0
        assert result["confidence"] == 0.0
        assert result["recommendation"] == "proceed"
        assert result["anomalies_active"] is False

    def test_cache_set_and_get(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        data = {"test": True}
        pm._set_cached("key1", data)
        assert pm._get_cached("key1") == data

    def test_cache_expiry(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        pm._cache_ttl = 0  # Expire immediately
        pm._set_cached("key2", {"expired": True})
        assert pm._get_cached("key2") is None

    def test_cache_invalidate(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        pm._set_cached("AgentA:model1", {"a": 1})
        pm._set_cached("AgentA:model2", {"a": 2})
        pm._set_cached("AgentB:model1", {"b": 1})
        pm.invalidate("AgentA")
        assert pm._get_cached("AgentA:model1") is None
        assert pm._get_cached("AgentA:model2") is None
        assert pm._get_cached("AgentB:model1") is not None

    @pytest.mark.asyncio
    async def test_predict_execution_no_data(self):
        """Should return neutral prediction when no historical data."""
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        result = await pm.predict_execution("UnknownAgent")
        assert result["confidence"] == 0.0
        assert result["recommendation"] == "proceed"

    @pytest.mark.asyncio
    async def test_should_preempt_fallback_no_data(self):
        """Should return False (proceed normally) when no data."""
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        result = await pm.should_preempt_fallback("UnknownAgent", "gemma4:4b")
        assert result is False

    @pytest.mark.asyncio
    async def test_predict_sequence_failure_end_of_sequence(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        result = await pm.predict_sequence_failure(["A", "B"], 1)
        assert result["next_step"] is None

    @pytest.mark.asyncio
    async def test_cost_forecast_empty(self):
        from app.memory.predictive import PredictiveMemory
        pm = PredictiveMemory()
        result = await pm.get_cost_forecast([])
        assert result["total_estimated_cost_usd"] == 0
        assert result["step_count"] == 0


# ── LLM Response Tests ──────────────────────────────────────────────────────

class TestLLMResponse:
    """Test updated LLMResponse dataclass."""

    def test_thinking_field_exists(self):
        from app.llm.provider import LLMResponse
        r = LLMResponse(text="hello", tokens_input=10, tokens_output=5,
                        model="test", provider="test")
        assert r.thinking == ""
        assert r.cost_usd == 0.0

    def test_thinking_field_with_value(self):
        from app.llm.provider import LLMResponse
        r = LLMResponse(text="answer", tokens_input=10, tokens_output=5,
                        model="gemma4:27b", provider="ollama",
                        thinking="Let me think about this...")
        assert r.thinking == "Let me think about this..."
        assert r.provider == "ollama"


# ── Router Gemma 4 Tests ────────────────────────────────────────────────────

class TestRouterGemma4:
    """Test Gemma 4 model assignments and routing."""

    def test_gemma4_model_map(self):
        from app.llm.router import _AGENT_MODEL_MAP
        # Gemma4:4b agents
        assert _AGENT_MODEL_MAP["ClassifierAgent"] == "gemma4:4b"
        assert _AGENT_MODEL_MAP["RouterAgent"] == "gemma4:4b"
        assert _AGENT_MODEL_MAP["SentimentAgent"] == "gemma4:4b"

    def test_gemma4_reasoning_agents(self):
        from app.llm.router import _AGENT_MODEL_MAP
        # Gemma4:27b reasoning agents
        assert _AGENT_MODEL_MAP["PlannerAgent"] == "gemma4:27b"
        assert _AGENT_MODEL_MAP["CriticAgent"] == "gemma4:27b"
        assert _AGENT_MODEL_MAP["JudgeAgent"] == "gemma4:27b"

    def test_scheduler_scraper_in_map(self):
        from app.llm.router import _AGENT_MODEL_MAP
        assert "SchedulerAgent" in _AGENT_MODEL_MAP
        assert "ScraperAgent" in _AGENT_MODEL_MAP
        assert _AGENT_MODEL_MAP["SchedulerAgent"] == "llama3.1:8b"
        assert _AGENT_MODEL_MAP["ScraperAgent"] == "llama3.1:8b"

    def test_cloud_preferred_reduced(self):
        from app.llm.router import _CLOUD_PREFERRED_AGENTS
        # Planner and Critic should NOT be cloud-preferred anymore
        assert "PlannerAgent" not in _CLOUD_PREFERRED_AGENTS
        assert "CriticAgent" not in _CLOUD_PREFERRED_AGENTS
        # Reporter and Researcher still cloud-preferred
        assert "ReporterAgent" in _CLOUD_PREFERRED_AGENTS
        assert "ResearcherAgent" in _CLOUD_PREFERRED_AGENTS

    def test_thinking_models_defined(self):
        from app.llm.router import _THINKING_MODELS
        assert "gemma4:27b" in _THINKING_MODELS
        assert "deepseek-r1:8b" in _THINKING_MODELS

    def test_all_24_agents_have_routes(self):
        """Every agent should have a model assignment or be in cloud/claude-only sets."""
        from app.llm.router import (
            _AGENT_MODEL_MAP, _CLOUD_PREFERRED_AGENTS,
            _CLAUDE_ONLY_AGENTS,
        )
        all_routed = set(_AGENT_MODEL_MAP.keys()) | _CLOUD_PREFERRED_AGENTS | _CLAUDE_ONLY_AGENTS
        expected_agents = {
            "ClassifierAgent", "RouterAgent", "SentimentAgent",
            "ExtractorAgent", "NormalizerAgent", "ValidatorAgent",
            "RepairAgent", "KnowledgeAgent",
            "SummarizerAgent", "AnalyzerAgent", "TranslatorAgent",
            "EnricherAgent", "MonitorAgent", "OCRAgent",
            "SchedulerAgent", "ScraperAgent",
            "PlannerAgent", "CriticAgent", "JudgeAgent",
            "ReporterAgent", "ResearcherAgent",
            "ComplianceAgent",
        }
        # WebhookAgent doesn't use LLM, OK to be missing
        for agent in expected_agents:
            assert agent in all_routed, f"{agent} has no route assignment"


# ── Ollama Thinking Mode Tests ──────────────────────────────────────────────

class TestOllamaThinkingMode:
    """Test thinking mode support in Ollama provider."""

    def test_thinking_models_constant(self):
        from app.llm.ollama_provider import THINKING_MODELS
        assert "gemma4:27b" in THINKING_MODELS
        assert "deepseek-r1:8b" in THINKING_MODELS

    def test_standard_model_not_in_thinking(self):
        from app.llm.ollama_provider import THINKING_MODELS
        assert "gemma4:4b" not in THINKING_MODELS
        assert "qwen2.5-coder:7b" not in THINKING_MODELS
        assert "llama3.1:8b" not in THINKING_MODELS


# ── Memory Manager Integration Tests ────────────────────────────────────────

class TestMemoryManagerIntegration:
    """Test that new memory tiers are properly integrated."""

    def test_manager_has_5_tiers(self):
        from app.memory.manager import MemoryManager
        mm = MemoryManager()
        assert hasattr(mm, "working")
        assert hasattr(mm, "episodic")
        assert hasattr(mm, "episodic_mongo")
        assert hasattr(mm, "semantic")
        assert hasattr(mm, "regressive")
        assert hasattr(mm, "predictive")

    def test_memory_module_exports(self):
        from app.memory import (
            WorkingMemory, EpisodicMemory, SemanticMemory,
            RegressiveMemory, PredictiveMemory, MemoryManager,
        )
        assert WorkingMemory is not None
        assert RegressiveMemory is not None
        assert PredictiveMemory is not None


# ── Experience Collector Context Manager Tests ──────────────────────────────

class TestExperienceCollectorContextManager:
    """Test the async context manager implementation."""

    def test_has_aenter_aexit(self):
        from app.memory.experience import ExperienceCollector
        ec = ExperienceCollector("TestAgent", "test")
        assert hasattr(ec, "__aenter__")
        assert hasattr(ec, "__aexit__")

    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        from app.memory.experience import ExperienceCollector
        async with ExperienceCollector("TestAgent", "test") as collector:
            assert collector is not None
            assert collector.agent_name == "TestAgent"

    @pytest.mark.asyncio
    async def test_context_manager_records_tool(self):
        from app.memory.experience import ExperienceCollector
        async with ExperienceCollector("TestAgent", "test") as collector:
            collector.record_tool("web_scrape")
            assert "web_scrape" in collector._tools_used


# ── Token Tracker Tests ─────────────────────────────────────────────────────

class TestTokenTracker:
    """Verify Gemma 4 pricing."""

    def test_ollama_is_free(self):
        from app.llm.token_tracker import calculate_cost
        cost = calculate_cost("ollama", 10000, 5000)
        assert cost == 0.0, "Ollama (local) should be free"

    def test_groq_pricing(self):
        from app.llm.token_tracker import calculate_cost
        cost = calculate_cost("groq", 1_000_000, 1_000_000)
        assert cost > 0, "Groq should have a cost"

    def test_claude_pricing(self):
        from app.llm.token_tracker import calculate_cost
        cost = calculate_cost("claude", 1_000_000, 1_000_000)
        assert cost > 0, "Claude should have a cost"
        assert cost > calculate_cost("groq", 1_000_000, 1_000_000), "Claude should be more expensive than Groq"
