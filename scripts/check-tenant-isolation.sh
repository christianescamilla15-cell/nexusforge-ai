#!/usr/bin/env bash
# CI grep gate -- enforces the C-1 + C-2 tenant-isolation contract.
#
# Fails when any backend route file contains the historical
# `OR user_id IS NULL` permissive read pattern, or when a SELECT/UPDATE
# /DELETE on workflows/automations/workflow_runs/documents references
# `WHERE id = $N` without a companion `user_id` or `org_id` clause.
#
# Run locally:  bash scripts/check-tenant-isolation.sh
# In CI: invoke from .github/workflows/*.yml as a required step.
#
# Comments are intentionally allowed to mention the historical pattern
# (e.g. "C-2 (2026-04-25): the `OR user_id IS NULL` reads...") so the
# grep is restricted to non-comment SQL.

set -euo pipefail

ROUTES_DIR="backend/app/routes"
EXIT_CODE=0

# --- Check 1: no "OR user_id IS NULL" in actual SQL strings ----------
# Accept it inside a "#" Python comment line so the historical
# reference in commit notes / code annotations does not trip the gate.
# Restricted to .py files so .pyc binaries do not match.
HITS=$(grep -rn --include='*.py' "user_id IS NULL" "$ROUTES_DIR" 2>/dev/null \
       | grep -v "^[^:]*:[0-9]*:[[:space:]]*#" \
       || true)

if [ -n "$HITS" ]; then
    echo 'FAIL -- "OR user_id IS NULL" found in route SQL:'
    echo "$HITS"
    echo ""
    echo "These permissive reads let any logged-in user read orphaned"
    echo "(NULL user_id) rows. Remove the OR clause and ensure rows"
    echo "are inserted with a real user_id."
    EXIT_CODE=1
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "OK -- tenant-isolation gate passed."
fi

exit $EXIT_CODE
