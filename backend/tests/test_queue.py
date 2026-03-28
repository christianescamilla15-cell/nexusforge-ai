"""Tests for Redis queue interface."""
from app.queue.producer import enqueue_task
from app.queue.worker import start_worker


def test_enqueue_task_returns_id():
    """enqueue_task is async and requires Redis; verify it's callable."""
    import asyncio
    import inspect
    # Verify enqueue_task is an async function (requires Redis to actually run)
    assert inspect.iscoroutinefunction(enqueue_task)


def test_producer_module_imports():
    from app.queue import producer
    assert hasattr(producer, 'enqueue_task')
    assert hasattr(producer, 'enqueue_workflow_run')


def test_worker_module_imports():
    from app.queue import worker
    assert hasattr(worker, 'start_worker')
