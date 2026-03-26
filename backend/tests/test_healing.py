"""Tests for self-healing system (Session 3)."""

import pytest
from app.healing.detector import FailureDetector, ErrorClassification
from app.healing.strategies import (
    HealingResult,
    HealingStrategy,
    RetryStrategy,
    SkipStrategy,
    RepairStrategy,
    EscalateStrategy,
    FallbackStrategy,
    STRATEGY_REGISTRY,
    get_strategy,
)


class TestFailureDetectorClassification:
    """Test error classification patterns."""

    def setup_method(self):
        self.detector = FailureDetector()

    def test_classifies_network_error(self):
        result = self.detector.classify("Connection refused to host")
        assert result.error_type == "network"
        assert result.is_recoverable is True
        assert result.suggested_action == "retry"

    def test_classifies_timeout_error(self):
        result = self.detector.classify("Request timed out after 30s")
        assert result.error_type == "timeout"
        assert result.is_recoverable is True
        assert result.suggested_action == "retry"

    def test_classifies_data_quality_error(self):
        result = self.detector.classify("Empty response, no data found")
        assert result.error_type == "data_quality"
        assert result.is_recoverable is True
        assert result.suggested_action == "skip"

    def test_classifies_llm_error(self):
        result = self.detector.classify("Content filter triggered by moderation system")
        assert result.error_type == "llm_error"
        assert result.is_recoverable is True
        assert result.suggested_action == "retry"

    def test_classifies_schema_mismatch(self):
        result = self.detector.classify("JSON parse error: unexpected token")
        assert result.error_type == "schema_mismatch"
        assert result.suggested_action == "repair"

    def test_classifies_rate_limit(self):
        result = self.detector.classify("429 Too many requests, rate limit hit")
        assert result.error_type == "network"
        assert result.is_recoverable is True
        assert result.suggested_action == "retry"

    def test_classifies_auth_error_not_recoverable(self):
        result = self.detector.classify("401 Unauthorized: invalid API key")
        assert result.error_type == "network"
        assert result.is_recoverable is False
        assert result.severity == "critical"
        assert result.suggested_action == "escalate"

    def test_unknown_error_with_info(self):
        result = self.detector.classify("Some very strange error that doesn't match any pattern at all")
        assert result.error_type == "unknown"
        assert result.severity == "high"
        assert result.is_recoverable is True  # has info (>20 chars)
        assert result.suggested_action == "repair"

    def test_unknown_error_short_message(self):
        result = self.detector.classify("fail")
        assert result.error_type == "unknown"
        assert result.is_recoverable is False  # <20 chars
        assert result.suggested_action == "escalate"

    def test_classification_returns_error_classification(self):
        result = self.detector.classify("connection reset")
        assert isinstance(result, ErrorClassification)
        assert hasattr(result, "error_type")
        assert hasattr(result, "severity")
        assert hasattr(result, "is_recoverable")
        assert hasattr(result, "suggested_action")


class TestHealingResult:
    """Test HealingResult dataclass."""

    def test_healing_result_fields(self):
        hr = HealingResult(
            success=True,
            strategy_used="retry",
            output={"result": "ok"},
            message="Retry succeeded",
        )
        assert hr.success is True
        assert hr.strategy_used == "retry"
        assert hr.output == {"result": "ok"}
        assert hr.message == "Retry succeeded"

    def test_healing_result_with_none_output(self):
        hr = HealingResult(success=False, strategy_used="escalate", output=None, message="Needs human review")
        assert hr.output is None


class TestStrategyRegistry:
    """Test strategy classes and registry."""

    def test_retry_strategy_exists(self):
        assert "retry" in STRATEGY_REGISTRY
        assert isinstance(STRATEGY_REGISTRY["retry"], RetryStrategy)

    def test_skip_strategy_exists(self):
        assert "skip" in STRATEGY_REGISTRY
        assert isinstance(STRATEGY_REGISTRY["skip"], SkipStrategy)

    def test_repair_strategy_exists(self):
        assert "repair" in STRATEGY_REGISTRY
        assert isinstance(STRATEGY_REGISTRY["repair"], RepairStrategy)

    def test_escalate_strategy_exists(self):
        assert "escalate" in STRATEGY_REGISTRY
        assert isinstance(STRATEGY_REGISTRY["escalate"], EscalateStrategy)

    def test_fallback_strategy_exists(self):
        assert "fallback" in STRATEGY_REGISTRY
        assert isinstance(STRATEGY_REGISTRY["fallback"], FallbackStrategy)

    def test_all_strategies_inherit_from_base(self):
        for name, strategy in STRATEGY_REGISTRY.items():
            assert isinstance(strategy, HealingStrategy), f"{name} is not a HealingStrategy"

    def test_get_strategy_returns_correct(self):
        s = get_strategy("retry")
        assert isinstance(s, RetryStrategy)

    def test_get_strategy_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown healing strategy"):
            get_strategy("nonexistent")

    def test_healing_strategy_is_abstract(self):
        with pytest.raises(TypeError):
            HealingStrategy()


class TestSkipStrategyExecution:
    """Test SkipStrategy apply method."""

    @pytest.mark.asyncio
    async def test_skip_returns_success(self):
        strategy = SkipStrategy()
        result = await strategy.apply(
            failed_step={"step_name": "extract"},
            error_info={"error_type": "data_quality"},
            context={},
        )
        assert isinstance(result, HealingResult)
        assert result.success is True
        assert result.strategy_used == "skip"
        assert result.output.get("_skipped") is True

    @pytest.mark.asyncio
    async def test_skip_uses_default_output(self):
        strategy = SkipStrategy()
        result = await strategy.apply(
            failed_step={"step_name": "extract"},
            error_info={"error_type": "data_quality"},
            context={"default_outputs": {"extract": {"entities": []}}},
        )
        assert result.output == {"entities": []}


class TestEscalateStrategyExecution:
    """Test EscalateStrategy apply method."""

    @pytest.mark.asyncio
    async def test_escalate_returns_failure(self):
        strategy = EscalateStrategy()
        result = await strategy.apply(
            failed_step={"step_name": "validate"},
            error_info={"error_type": "network", "severity": "critical"},
            context={},
        )
        assert result.success is False
        assert result.strategy_used == "escalate"
        assert "human review" in result.message


class TestFallbackStrategyExecution:
    """Test FallbackStrategy apply method."""

    @pytest.mark.asyncio
    async def test_fallback_with_cache(self):
        strategy = FallbackStrategy()
        result = await strategy.apply(
            failed_step={"step_name": "classify"},
            error_info={},
            context={"result_cache": {"classify": {"category": "legal"}}},
        )
        assert result.success is True
        assert result.output == {"category": "legal"}

    @pytest.mark.asyncio
    async def test_fallback_without_cache(self):
        strategy = FallbackStrategy()
        result = await strategy.apply(
            failed_step={"step_name": "classify"},
            error_info={},
            context={},
        )
        assert result.success is False
        assert "No cached result" in result.message
