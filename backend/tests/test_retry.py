"""Tests for retry policy: exponential backoff, jitter, and error filtering."""

import pytest
from app.engine.retry_policy import RetryPolicy


def test_should_retry_first_attempt():
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry(0, RuntimeError("timeout")) is True


def test_should_retry_second_attempt():
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry(1, RuntimeError("timeout")) is True


def test_should_retry_false_after_max():
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry(3, RuntimeError("timeout")) is False


def test_should_retry_false_for_validation_error():
    policy = RetryPolicy(max_retries=5)
    assert policy.should_retry(0, ValueError("validation failed")) is False


def test_should_retry_false_for_unauthorized():
    policy = RetryPolicy(max_retries=5)
    assert policy.should_retry(0, RuntimeError("unauthorized access")) is False


def test_should_retry_false_for_forbidden():
    policy = RetryPolicy(max_retries=5)
    assert policy.should_retry(0, RuntimeError("403 forbidden")) is False


def test_get_delay_exponential_growth():
    policy = RetryPolicy(base_delay=1.0, max_delay=30.0)
    assert policy.get_delay(0) == 1.0
    assert policy.get_delay(1) == 2.0
    assert policy.get_delay(2) == 4.0
    assert policy.get_delay(3) == 8.0


def test_get_delay_capped_at_max():
    policy = RetryPolicy(base_delay=1.0, max_delay=10.0)
    assert policy.get_delay(10) == 10.0
    assert policy.get_delay(20) == 10.0


def test_default_values():
    policy = RetryPolicy()
    assert policy.max_retries == 3
    assert policy.base_delay == 1.0
    assert policy.max_delay == 30.0
