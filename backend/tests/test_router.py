"""Tests for LLM router circuit breaker and token cost tracking."""

import time
import pytest
from app.llm.router import _CircuitBreaker, _CB_ERROR_THRESHOLD
from app.llm.token_tracker import calculate_cost


# ---------- Circuit breaker ----------

def test_circuit_breaker_starts_closed():
    cb = _CircuitBreaker()
    assert cb.is_open() is False


def test_circuit_breaker_opens_after_threshold():
    cb = _CircuitBreaker()
    for _ in range(_CB_ERROR_THRESHOLD):
        cb.record_error()
    assert cb.is_open() is True


def test_circuit_breaker_stays_closed_below_threshold():
    cb = _CircuitBreaker()
    for _ in range(_CB_ERROR_THRESHOLD - 1):
        cb.record_error()
    assert cb.is_open() is False


def test_circuit_breaker_reset():
    cb = _CircuitBreaker()
    for _ in range(_CB_ERROR_THRESHOLD):
        cb.record_error()
    assert cb.is_open() is True
    cb.reset()
    assert cb.is_open() is False


# ---------- Token tracker cost ----------

def test_groq_cost_calculation():
    cost = calculate_cost("groq", 1000, 500)
    expected = 1000 * (0.59 / 1_000_000) + 500 * (0.79 / 1_000_000)
    assert abs(cost - expected) < 1e-10


def test_claude_cost_calculation():
    cost = calculate_cost("claude", 1000, 500)
    expected = 1000 * (3.0 / 1_000_000) + 500 * (15.0 / 1_000_000)
    assert abs(cost - expected) < 1e-10


def test_cost_always_positive():
    assert calculate_cost("groq", 100, 50) > 0
    assert calculate_cost("claude", 100, 50) > 0


def test_zero_tokens_zero_cost():
    assert calculate_cost("groq", 0, 0) == 0.0
    assert calculate_cost("claude", 0, 0) == 0.0


def test_unknown_provider_zero_cost():
    assert calculate_cost("unknown_provider", 1000, 500) == 0.0
