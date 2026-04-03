# NexusForge Execution Fix — Bugfix Design

## Overview

Two bugs prevent the NexusForge execution system from working correctly on Render, where Redis is not configured.

Bug 1 — `execute_workflow()` in `backend/app/engine/executor.py` must handle Redis unavailability gracefully. The current file already contains a `safe_publish()` helper and a `try/except` block around `get_redis()` + `redis.ping()`. **Key finding**: `get_redis()` uses `aioredis.from_url()` which is lazy and never raises on construction — the failure only surfaces on the first network call (`redis.ping()` or `redis.publish()`). The existing guard already catches this. The design must verify no remaining call sites bypass `safe_publish()` and that the `workflow_runs` row is always updated to a terminal state.

Bug 2 — `ExecutionDetailPage` generates synthetic LiveLog events from `steps[]` returned by `GET /api/executions/{run_id}`. The event-generation block (lines 99–140) is correct in structure but only fires when `mapped.steps.length > 0`. Because Bug 1 prevented steps from being written to `step_executions`, `steps[]` was always empty. Once Bug 1 is confirmed fixed, the event-generation logic must be verified to correctly map the `StepExecutionResponse` shape (fields: `step_name`, `agent_type`, `status`, `duration_ms`, `tokens_used`, `error_message`) to the display fields it reads (`step.name`, `step.agent_type`, `step.tokens`, `step.error`).

Additionally, 7 zombie runs (status `cancelled`) exist in the database. A `/api/executions/cleanup-zombies` route already exists and can be called to resolve them.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — Redis is unavailable AND `execute_workflow()` is called, OR `steps[]` is empty when the API returns a completed/failed run
- **Property (P)**: The desired behavior — workflow steps execute and are persisted regardless of Redis availability; LiveLog shows real step events when steps exist
- **Preservation**: Existing behavior when Redis IS available, step failure handling, checkpoint resume, and demo data fallback must remain unchanged
- **`safe_publish(redis, channel, data)`**: Helper in `executor.py` that publishes to Redis if available, silently skips if `redis is None` or publish raises
- **`get_redis()`**: Returns a lazy `aioredis` client from `db/client.py`; never raises on construction, only on first network call
- **`isBugCondition`**: Pseudocode function identifying inputs that trigger the bugs
- **zombie run**: A `workflow_runs` row stuck in `pending`, `running`, or `cancelled` with no `completed_at`, caused by executor crashes before the fix

## Bug Details

### Bug Condition

**Bug 1** manifests when `execute_workflow()` is called and Redis is unreachable. The `aioredis` client is constructed lazily, so `get_redis()` succeeds, but the subsequent `redis.ping()` raises a connection error. If this exception is not caught, the entire coroutine aborts before any step runs, leaving the run in `running` state forever.

**Bug 2** manifests when `ExecutionDetailPage` receives a run where `data.steps` is an empty array (or absent). The event-generation block is gated on `mapped.steps.length > 0`, so no `step_started`/`step_completed` events are generated. The fallback path only emits a generic warning or completion summary — no per-step detail.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { redisAvailable: bool, stepsArray: list, runStatus: str }
  OUTPUT: boolean

  -- Bug 1 condition
  IF NOT input.redisAvailable
     AND execute_workflow_called(input)
     AND NOT redis_exception_caught(input)
  THEN RETURN true

  -- Bug 2 condition
  IF input.stepsArray.length == 0
     AND input.runStatus IN ['completed', 'failed']
     AND livelog_shows_no_step_events(input)
  THEN RETURN true

  RETURN false
END FUNCTION
```

### Examples

- **Bug 1 — Redis down, run stuck**: Trigger a workflow on Render. `redis.ping()` raises `ConnectionError`. No steps execute. `workflow_runs.status` stays `running`. `step_executions` has 0 rows for this run.
- **Bug 1 — Redis down, safe_publish gap**: If any `redis.publish()` call exists outside `safe_publish()`, it raises mid-execution and aborts the workflow even after the initial ping guard.
- **Bug 2 — Empty steps, empty log**: Open `ExecutionDetailPage` for a run that completed but has 0 rows in `step_executions`. `mapped.steps = []`. LiveLog shows only "Run started" info event and a generic completion line — no per-step events.
- **Bug 2 — Field name mismatch**: API returns `step_name` but frontend reads `step.name` (mapped correctly in `ExecutionDetailPage`). API returns `tokens_used` but frontend reads `step.tokens` (also mapped). These mappings must be verified end-to-end.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- When Redis IS available, all `run_started`, `group_started`, `step_completed`, `run_completed`, and `run_failed` events must continue to be published to `run:{run_id}` via Redis pub/sub
- When a workflow step fails after all retries, the run must still be marked `failed` with `error_message` and `completed_at` set
- When a workflow completes successfully, the run must still be marked `completed` with `total_tokens`, `total_cost_usd`, and `completed_at` set
- Checkpoint resume must still skip already-completed steps
- `ExecutionDetailPage` with no steps and status `pending`/`running` must still show the waiting/stuck warning
- `ExecutionDetailPage` fetch errors must still fall back to `DEMO_EXECUTION` and `DEMO_EVENTS`

**Scope:**
All inputs where Redis IS available and reachable are completely unaffected by the Bug 1 fix. All `ExecutionDetailPage` renders where `steps[]` is non-empty are unaffected by the Bug 2 fix.

## Hypothesized Root Cause

### Bug 1

1. **Lazy Redis client + missing ping guard (original state)**: `get_redis()` returns a client without connecting. The first real network call (`redis.ping()` or `redis.publish()`) raises. If uncaught, the coroutine dies. **Current state**: The executor already has a `try/except` around `get_redis()` + `redis.ping()` that sets `redis = None` on failure. This guard appears correct.

2. **Residual direct publish calls**: Any `redis.publish()` call that bypasses `safe_publish()` would still crash if `redis` is not `None` but the connection drops mid-execution. **Verification needed**: Confirm all publish calls in `executor.py` go through `safe_publish()`.

3. **`asyncio.create_task()` swallows exceptions**: Unhandled exceptions inside a task are only logged at task destruction, not propagated. This means a crash in `execute_workflow()` is invisible to the caller. The fix is ensuring the function never raises unhandled — it must always reach a `return` statement that updates `workflow_runs`.

4. **Zombie runs from pre-fix crashes**: Runs created before the fix was in place are stuck in `running`/`pending`. The `/cleanup-zombies` endpoint handles these.

### Bug 2

5. **Causal dependency on Bug 1**: The primary cause of empty `steps[]` is that Bug 1 prevented `run_step()` from ever being called, so `step_executions` has no rows. Once Bug 1 is fixed, real step data will flow.

6. **Field mapping verification**: The frontend maps `s.step_name → name`, `s.tokens_used → tokens`, `s.cost_usd → cost`, `s.error_message → error`. These must match what `StepExecutionResponse` serializes. A mismatch would cause `step.tokens` or `step.name` to be `undefined`, producing broken event detail strings.

## Correctness Properties

Property 1: Bug Condition — Redis-Resilient Execution

_For any_ call to `execute_workflow()` where Redis is unavailable (connection refused, timeout, or `ping()` raises), the fixed function SHALL complete execution of all workflow steps, write at least one row per executed step to `step_executions`, and update `workflow_runs.status` to either `completed` or `failed` with a valid `completed_at` timestamp — never leaving the run in `running` or `pending` state.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation — Redis-Available Behavior Unchanged

_For any_ call to `execute_workflow()` where Redis IS available and reachable, the fixed function SHALL produce exactly the same sequence of Redis publish events (`run_started`, `group_started`, `step_completed`/`step_failed`, `run_completed`/`run_failed`) as the original function, preserving all live event broadcasting behavior.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 3: Bug Condition — LiveLog Event Generation

_For any_ `ExecutionDetailPage` render where `GET /api/executions/{run_id}` returns a non-empty `steps[]` array, the fixed component SHALL generate exactly two events per step (`step_started` and either `step_completed` or `step_failed`), plus one leading `info` event for run start — resulting in `(steps.length * 2) + 1` total events in the LiveLog.

**Validates: Requirements 2.5**

Property 4: Preservation — LiveLog Fallback Behavior Unchanged

_For any_ `ExecutionDetailPage` render where `steps[]` is empty and status is `pending` or `running`, the fixed component SHALL continue to display the waiting/stuck warning event unchanged. For any render where the fetch fails, it SHALL continue to fall back to `DEMO_EXECUTION` and `DEMO_EVENTS` unchanged.

**Validates: Requirements 3.5, 3.6**

## Fix Implementation

### Changes Required

**File**: `backend/app/engine/executor.py`

**Verification (not a change — confirm existing code is correct):**
1. **Redis guard**: Confirm the `try/except` block around `get_redis()` + `redis.ping()` sets `redis = None` on any exception. Current code does this correctly.
2. **All publish calls use `safe_publish()`**: Audit every `redis.publish` call site. Current code routes all publishes through `safe_publish()`. Confirm no direct calls remain.
3. **Terminal state guarantee**: Confirm the outer `except Exception` block always updates `workflow_runs` to `failed` with `completed_at`. Current code does this.

**If gaps are found during exploratory testing:**
- Replace any direct `await redis.publish(...)` with `await safe_publish(redis, ...)` 
- Ensure `safe_publish()` catches all exception types, not just `Exception` base class

---

**File**: `frontend/src/features/executions/ExecutionDetailPage.jsx`

**Verification (confirm field mapping is correct):**
1. **`step.name`**: Mapped from `s.step_name` — matches `StepExecutionResponse.step_name` ✓
2. **`step.tokens`**: Mapped from `s.tokens_used` — matches `StepExecutionResponse.tokens_used` ✓
3. **`step.cost`**: Mapped from `s.cost_usd` — matches `StepExecutionResponse.cost_usd` ✓
4. **`step.error`**: Mapped from `s.error_message` — matches `StepExecutionResponse.error_message` ✓
5. **`step.agent_type`**: Mapped from `s.agent_type || s.step_type` — matches `StepExecutionResponse.agent_type` ✓

**No code changes required in `ExecutionDetailPage.jsx`** if the field mappings are confirmed correct. The LiveLog will populate automatically once Bug 1 is fixed and real step data flows.

---

**Operational fix (one-time):**

Call `POST /api/executions/cleanup-zombies` to mark the 7 stuck runs as `failed` with a descriptive `error_message`. This route already exists and applies a 10-minute age threshold.

## Testing Strategy

### Validation Approach

Two-phase approach: first run exploratory tests on the current (potentially unfixed) code to confirm or refute the root cause hypotheses, then run fix-checking and preservation tests to validate correctness.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE assuming the fix is complete. The executor already appears to have the fix — exploratory tests will confirm this or reveal remaining gaps.

**Test Plan**: Mock `get_redis()` to raise `ConnectionRefusedError` and call `execute_workflow()` with a minimal DAG. Assert that steps execute and `workflow_runs` reaches a terminal state.

**Test Cases**:
1. **Redis-down full execution**: Mock Redis as unavailable, run a 2-step DAG, assert both steps complete and `workflow_runs.status = 'completed'` (will pass if fix is in place, fail if not)
2. **Redis-down step failure**: Mock Redis as unavailable, run a DAG where step 1 fails, assert `workflow_runs.status = 'failed'` with `error_message` set
3. **Mid-execution Redis drop**: Mock Redis to succeed on `ping()` but raise on `publish()`, assert `safe_publish()` swallows the error and execution continues
4. **Empty steps LiveLog**: Render `ExecutionDetailPage` with `steps = []` and `status = 'completed'`, assert LiveLog contains the generic completion event (not a crash)

**Expected Counterexamples** (if fix is NOT in place):
- `workflow_runs.status` remains `running` after execution attempt
- `step_executions` has 0 rows for the run
- Possible causes: unguarded `redis.ping()`, direct `redis.publish()` call outside `safe_publish()`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed functions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := execute_workflow_fixed(input)  -- with Redis mocked as unavailable
  ASSERT result.status IN ['completed', 'failed']
  ASSERT workflow_runs[input.run_id].completed_at IS NOT NULL
  ASSERT step_executions.count(run_id=input.run_id) >= expected_step_count
END FOR

FOR ALL render WHERE isBugCondition(render) DO  -- steps[] non-empty
  events := generateEvents(render.steps)
  ASSERT events.length == (render.steps.length * 2) + 1
  ASSERT ALL step IN render.steps: events contains step_started(step.name)
  ASSERT ALL step IN render.steps: events contains step_completed(step.name) OR step_failed(step.name)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed functions produce the same result as the original functions.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO  -- Redis available
  events_original := capture_redis_publishes(execute_workflow_original(input))
  events_fixed    := capture_redis_publishes(execute_workflow_fixed(input))
  ASSERT events_original == events_fixed
END FOR

FOR ALL render WHERE NOT isBugCondition(render) DO  -- steps[] empty + pending/running
  events_original := generateEvents_original(render)
  events_fixed    := generateEvents_fixed(render)
  ASSERT events_original == events_fixed  -- waiting warning unchanged
END FOR
```

**Testing Approach**: Property-based testing is recommended for the Redis-available preservation check because it can generate many DAG shapes and Redis availability patterns automatically, catching edge cases like single-step DAGs, parallel groups, and checkpoint-resume scenarios.

**Test Cases**:
1. **Redis-available publish sequence**: With Redis mocked as available, verify all expected channel messages are published in order
2. **Step failure propagation**: Verify a failing step still marks the run `failed` and records `error_message` after the fix
3. **Checkpoint resume**: Verify already-completed steps are skipped when `get_completed_steps()` returns them
4. **Demo data fallback**: Verify `ExecutionDetailPage` still renders `DEMO_EXECUTION` when `fetchAPI` throws

### Unit Tests

- `test_safe_publish_with_none_redis`: Call `safe_publish(None, "channel", "data")` — assert no exception raised, returns `None`
- `test_safe_publish_with_failing_redis`: Call `safe_publish(mock_redis_that_raises, ...)` — assert no exception raised
- `test_execute_workflow_redis_down`: Mock `get_redis()` to raise, run minimal DAG, assert terminal state
- `test_execute_workflow_redis_publish_fails`: Mock `redis.publish()` to raise mid-execution, assert execution completes
- `test_livelog_event_count`: Given N steps, assert `generateEvents` produces `(N * 2) + 1` events
- `test_livelog_empty_steps_pending`: Given `steps=[]` and `status='running'`, assert warning event is generated

### Property-Based Tests

- Generate random DAG configurations (1–10 steps, random dependencies) with Redis mocked as unavailable — assert `workflow_runs` always reaches a terminal state and `step_executions` row count equals executed step count
- Generate random step arrays (0–20 steps, random statuses) — assert LiveLog event count follows the `(N * 2) + 1` formula for N > 0, and fallback warning for N = 0
- Generate random Redis availability sequences (available/unavailable per call) — assert `safe_publish()` never raises regardless of Redis state

### Integration Tests

- Trigger a real workflow execution against the Render backend with Redis confirmed down via `/api/health` — assert the run reaches `completed` or `failed` within 60 seconds
- Call `POST /api/executions/cleanup-zombies` — assert the 7 zombie runs are marked `failed` with `completed_at` set
- Open `ExecutionDetailPage` for a newly completed run — assert LiveLog shows per-step events matching the `step_executions` rows
