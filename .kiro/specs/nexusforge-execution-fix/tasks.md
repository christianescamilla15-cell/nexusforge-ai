# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Redis-Unavailable Executor Crash
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate Bug 1 (executor crash) and Bug 2 (empty LiveLog) exist
  - **Scoped PBT Approach**: Scope to concrete failing cases — `redisAvailable=False` with a 2-step DAG; `steps=[]` with `status='completed'`
  - Create `backend/tests/test_executor_redis_resilience.py`
  - Mock `get_redis()` to raise `ConnectionRefusedError` on construction (simulates Render environment)
  - Call `execute_workflow()` with a minimal 2-step sequential DAG
  - Assert `workflow_runs.status` is `'completed'` or `'failed'` (never `'running'` or `'pending'`)
  - Assert `workflow_runs.completed_at` is NOT NULL
  - Assert `step_executions` has at least 1 row for the run
  - Also test mid-execution Redis drop: mock `redis.ping()` to succeed but `redis.publish()` to raise — assert execution still completes
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS if fix is not in place (proves bug exists); PASSES if fix is already in place (confirms verification-first approach)
  - Document counterexamples found (e.g., `workflow_runs.status = 'running'` after execution attempt)
  - Mark task complete when test is written, run, and outcome is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Redis-Available Publish Sequence Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: with Redis mocked as available, `execute_workflow()` publishes `run_started`, `group_started`, `step_completed`, `run_completed` events in order on UNFIXED code
  - Observe: `ExecutionDetailPage` with `steps=[]` and `status='running'` shows waiting warning event on UNFIXED code
  - Observe: `ExecutionDetailPage` fetch error falls back to `DEMO_EXECUTION` and `DEMO_EVENTS` on UNFIXED code
  - Create `backend/tests/test_executor_preservation.py`
  - Write property-based test: for all DAG shapes (1–5 steps, random dependencies) where Redis IS available, capture all `redis.publish()` call args and assert the sequence matches `[run_started, group_started*, step_completed|step_failed*, run_completed|run_failed]`
  - Write property-based test: for all step arrays of length N > 0, assert `generateEvents(steps)` produces exactly `(N * 2) + 1` events
  - Write unit test: `steps=[]` + `status='running'` → warning event generated; `steps=[]` + `status='completed'` → generic completion event generated
  - Write unit test: fetch error → `DEMO_EXECUTION` and `DEMO_EVENTS` rendered
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 3. Fix for Redis-unavailable executor crash and empty LiveLog

  - [ ] 3.1 Audit and patch executor.py
    - Re-read `backend/app/engine/executor.py` in full
    - Verify the `try/except` around `get_redis()` + `redis.ping()` sets `redis = None` on any exception (lines ~30–35)
    - Audit every `redis.publish` call site — confirm ALL go through `safe_publish()` with no direct `await redis.publish(...)` calls remaining
    - Verify the outer `except Exception` block at the bottom always updates `workflow_runs` to `failed` with `completed_at` set
    - If any direct `redis.publish()` call is found: replace with `await safe_publish(redis, channel, data)`
    - If `safe_publish()` only catches `Exception` base class: confirm it also handles `asyncio.CancelledError` and `BaseException` subclasses that could escape
    - _Bug_Condition: `isBugCondition(input)` where `input.redisAvailable = False` AND `execute_workflow_called = True`_
    - _Expected_Behavior: `workflow_runs.status IN ['completed', 'failed']` AND `completed_at IS NOT NULL` AND `step_executions.count >= expected_steps`_
    - _Preservation: Redis-available publish sequence must remain identical; step failure propagation, checkpoint resume, and terminal state writes must be unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [ ] 3.2 Verify field mappings in ExecutionDetailPage.jsx
    - Confirm `s.step_name → step.name` mapping (line ~107)
    - Confirm `s.tokens_used → step.tokens` mapping (line ~112)
    - Confirm `s.cost_usd → step.cost` mapping (line ~113)
    - Confirm `s.error_message → step.error` mapping (line ~117)
    - Confirm `s.agent_type || s.step_type → step.agent_type` mapping (line ~108)
    - No code changes expected — this is a verification step
    - If any mismatch is found: apply the minimal fix to align the field name with `StepExecutionResponse`
    - _Requirements: 2.5_

  - [ ] 3.3 Call cleanup-zombies endpoint
    - Call `POST /api/executions/cleanup-zombies` to mark the 7 zombie runs as `failed`
    - Verify response confirms runs were updated with `completed_at` set
    - _Requirements: 2.2_

  - [ ] 3.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Redis-Unavailable Executor Completes
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (terminal state + step rows written)
    - Run `backend/tests/test_executor_redis_resilience.py` on the patched code
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 1 is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Redis-Available Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run `backend/tests/test_executor_preservation.py` on the patched code
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in Redis-available path, LiveLog fallback, and demo data)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite: `pytest backend/tests/test_executor_redis_resilience.py backend/tests/test_executor_preservation.py -v`
  - Confirm Property 1 (Bug Condition) passes — executor completes with Redis down
  - Confirm Property 2 (Preservation) passes — Redis-available behavior unchanged
  - Open `ExecutionDetailPage` for a newly completed run and verify LiveLog shows per-step events
  - Confirm the 7 zombie runs show `status='failed'` with `completed_at` set in the database
  - Ask the user if any questions arise before closing the spec
