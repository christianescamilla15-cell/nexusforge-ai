#!/usr/bin/env bash
# Functionality smoke layer — exercises the platform's golden paths
# against the live verify stack and writes one functionality.json that
# feeds the triangulator.
#
# Each "test" here is a Pythonic httpx call (sync, easy to read in the
# triangulation report). Failures are recorded as findings with
# category="functionality" and severity tied to the surface importance:
#
#   critical: auth, /api/health, chat round-trip
#   high:     wizard, workflow CRUD+run, refactor ingest
#   medium:   synthesizer build (full E2E with file-write), Mythos scan
#   low:      audit log, executions DB-backed timeline
#
# The harness lives in verification/_smoke_harness.py — a single
# source of truth for what flows are exercised. This shell script just
# runs it and persists the JSON.
#
# Usage:
#   bash verification/functionality_smoke.sh <tool_id> <run_id>
set -euo pipefail

TOOL_ID="${1:?missing tool_id}"
RUN_ID="${2:?missing run_id}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$REPO_ROOT/verification/reports/$TOOL_ID/$RUN_ID"
mkdir -p "$REPORT_DIR"

if [[ ! -f "$REPORT_DIR/run_metadata.json" ]]; then
    echo "✗ no metadata for $REPORT_DIR — run bootstrap.sh first"
    exit 1
fi

echo "═══ functionality_smoke.sh — tool=$TOOL_ID run=$RUN_ID ═══"

python3 "$REPO_ROOT/verification/_smoke_harness.py" \
    --base-url http://localhost:18000 \
    --frontend-url http://localhost:15173 \
    --tool-id "$TOOL_ID" \
    --run-id "$RUN_ID" \
    --output "$REPORT_DIR/functionality_findings.json"

PASS=$(python3 -c "
import json
data = json.load(open('$REPORT_DIR/functionality_findings.json'))
total = data['summary']['total']
passed = data['summary']['passed']
print(f'{passed}/{total} passed')
")
echo "✓ Smoke complete: $PASS"
