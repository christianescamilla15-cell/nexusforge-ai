# Bugfix Requirements Document

## Introduction

Two bugs are preventing the NexusForge Execution System from functioning correctly in the Render deployment environment.

Bug 1 (CRITICAL): `execute_workflow()` silently crashes when Redis is unavailable. Because Redis is not configured on Render, `get_redis()` raises an exception that is unhandled, causing the entire async task to die before any step executes. No steps are recorded, no error is written to the database, and the run stays in `pending` or `running` state indefinitely.

Bug 2 (Dependent): `ExecutionDetailPage` generates synthetic LiveLog events from `steps[]` returned by `GET /api/executions/{run_id}`. Because Bug 1 prevents any steps from being written to `step_executions`, `steps[]` is always empty and the LiveLog shows no meaningful activity. Once Bug 1 is fixed and real step data flows into the database, the event-generation logic (lines 99–140) must correctly produce `step_started` / `step_completed` / `step_failed` events for every step.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `execute_workflow()` is launched via `asyncio.create_task()` AND Redis is unavailable THEN the system raises an unhandled exception inside the task, silently terminating execution before any step runs

1.2 WHEN `get_redis()` fails AND no fallback is in place THEN the system leaves the `workflow_runs` row in `running` status with no `error_message` and no `completed_at` timestamp

1.3 WHEN `redis.publish()` is called on a None or disconnected Redis client THEN the system raises an exception that propagates up and aborts the workflow mid-execution

1.4 WHEN `execute_workflow()` crashes before calling `run_step()` THEN the system writes zero rows to `step_executions` for that run

1.5 WHEN `GET /api/executions/{run_id}` returns a run with an empty `steps[]` array THEN the system generates no `step_started` or `step_completed` events in the LiveLog, showing only a generic warning or nothing

### Expected Behavior (Correct)

2.1 WHEN `execute_workflow()` is launched AND Redis is unavailable THEN the system SHALL continue executing all workflow steps without Redis, logging a warning that live event broadcasting is disabled

2.2 WHEN `get_redis()` fails THEN the system SHALL set `redis = None` and proceed, ensuring the `workflow_runs` row is updated to `failed` or `completed` with a valid `completed_at` timestamp

2.3 WHEN `redis.publish()` would be called with `redis = None` THEN the system SHALL skip the publish silently via a `safe_publish()` helper without raising any exception

2.4 WHEN `execute_workflow()` completes (successfully or with a step failure) THEN the system SHALL write at least one row per executed step into `step_executions`

2.5 WHEN `GET /api/executions/{run_id}` returns a run with a non-empty `steps[]` array THEN the system SHALL generate a `step_started` event and a `step_completed` or `step_failed` event for each step in the LiveLog

### Unchanged Behavior (Regression Prevention)

3.1 WHEN Redis IS available and reachable THEN the system SHALL CONTINUE TO publish all run and step events to the `run:{run_id}` channel as before

3.2 WHEN a workflow step fails after all retries THEN the system SHALL CONTINUE TO mark the run as `failed`, record the error message, and write the step result to `step_executions`

3.3 WHEN a workflow completes successfully THEN the system SHALL CONTINUE TO mark the run as `completed`, record `total_tokens` and `total_cost_usd`, and return the full results dict

3.4 WHEN `execute_workflow()` resumes from a checkpoint THEN the system SHALL CONTINUE TO skip already-completed steps and only execute pending ones

3.5 WHEN `ExecutionDetailPage` receives a run with no steps and status `pending` or `running` THEN the system SHALL CONTINUE TO display the appropriate waiting/stuck warning in the LiveLog

3.6 WHEN `ExecutionDetailPage` receives a run that falls back to demo data due to a fetch error THEN the system SHALL CONTINUE TO display the DEMO_EXECUTION steps and DEMO_EVENTS unchanged
