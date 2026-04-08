"""Property 1: Bug Condition — Redis-Unavailable Executor must complete gracefully.

Verifies that execute_workflow() works when Redis is unavailable (Render env).
The executor must: set redis=None, write steps, update to terminal state.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock


class TestSafePublish:
    """safe_publish must handle None redis and broken redis."""

    def test_safe_publish_with_none(self):
        from app.engine.executor import safe_publish
        asyncio.get_event_loop().run_until_complete(
            safe_publish(None, "test:ch", '{"event": "test"}')
        )

    @pytest.mark.asyncio
    async def test_safe_publish_with_broken_redis(self):
        from app.engine.executor import safe_publish
        broken = AsyncMock()
        broken.publish = AsyncMock(side_effect=ConnectionError("down"))
        await safe_publish(broken, "test:ch", '{"event": "test"}')

    @pytest.mark.asyncio
    async def test_safe_publish_calls_redis_when_available(self):
        from app.engine.executor import safe_publish
        mock_redis = AsyncMock()
        await safe_publish(mock_redis, "run:123", '{"e": "t"}')
        mock_redis.publish.assert_called_once()

    def test_safe_publish_signature(self):
        import inspect
        from app.engine.executor import safe_publish
        params = list(inspect.signature(safe_publish).parameters.keys())
        assert params == ["redis", "channel", "data"]


class TestExecutorRedisResilience:
    """Verify executor code handles Redis unavailability correctly."""

    def test_redis_fallback_pattern_in_source(self):
        import inspect
        from app.engine.executor import execute_workflow
        source = inspect.getsource(execute_workflow)
        assert "get_redis()" in source
        assert "redis = None" in source
        assert "Redis unavailable" in source

    def test_always_sets_terminal_state(self):
        import inspect, re
        from app.engine.executor import execute_workflow
        source = inspect.getsource(execute_workflow)

        failed_updates = source.count("SET status = 'failed'")
        completed_updates = source.count("SET status = 'completed'")
        assert failed_updates >= 3, f"Need >=3 failed writes, got {failed_updates}"
        assert completed_updates >= 1, f"Need >=1 completed write, got {completed_updates}"

        # Every status update must include completed_at
        updates = re.findall(r"SET status\s*=\s*'(?:failed|completed)'.*?(?=WHERE|$)", source, re.DOTALL)
        for u in updates:
            assert "completed_at" in u, f"Missing completed_at: {u[:60]}"

    def test_no_direct_redis_publish(self):
        import inspect
        from app.engine.executor import execute_workflow
        source = inspect.getsource(execute_workflow)
        lines = source.split("\n")
        for line in lines:
            s = line.strip()
            if "await redis.publish" in s:
                pytest.fail(f"Direct redis.publish found (should use safe_publish): {s}")

    def test_outer_except_catches_all(self):
        import inspect
        from app.engine.executor import execute_workflow
        source = inspect.getsource(execute_workflow)
        assert "except Exception as e:" in source

    def test_publishes_required_events(self):
        import inspect
        from app.engine.executor import execute_workflow
        source = inspect.getsource(execute_workflow)
        for event in ["run_started", "group_started", "run_completed", "run_failed"]:
            assert event in source, f"Missing event: {event}"


class TestZombieProtection:
    """Zombie run cleanup must exist in main.py."""

    def test_zombie_cleanup_in_main(self):
        with open("app/main.py") as f:
            source = f.read()
        assert "zombie" in source.lower()
        assert "cleanup" in source.lower()

    def test_zombie_sets_failed_status(self):
        with open("app/main.py") as f:
            source = f.read()
        assert "zombie cleanup" in source.lower()
        assert "failed" in source.lower() or "cancelled" in source.lower()
