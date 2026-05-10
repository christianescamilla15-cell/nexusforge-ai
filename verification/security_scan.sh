#!/usr/bin/env bash
# Security scan layer — runs every detector once and writes one
# unified findings.json that feeds the triangulator.
#
# Why all of these and not just Mythos:
#   - Mythos is intra-app (knows the FastAPI/React surface). It's
#     blind to dependency CVEs and to historical secrets in git.
#   - pip-audit / npm audit cover the dep CVE surface.
#   - gitleaks covers historical secret leaks across the full git
#     history (not just the working tree).
#   - semgrep adds language-agnostic SAST rulesets (auth bypasses,
#     SSRF, unsafe deserialization) that supplement Mythos's regex
#     pass.
#   - schemathesis fuzzes the live OpenAPI surface — finds 5xx
#     crashes, schema/response mismatches, and auth-bypass on
#     unprotected routes.
#
# All output → ONE merged findings.json with the contract documented
# in verification/templates/finding.schema.json.
#
# Usage:
#   bash verification/security_scan.sh <tool_id> <run_id>
set -euo pipefail

TOOL_ID="${1:?missing tool_id}"
RUN_ID="${2:?missing run_id}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$REPO_ROOT/verification/reports/$TOOL_ID/$RUN_ID"
RAW_DIR="$REPORT_DIR/raw"
mkdir -p "$RAW_DIR"

# Cross-platform Python detection (mirrors bootstrap.sh): prefer python3,
# fall back to python (Windows). Reuse the env var if the parent set it.
if [[ -z "${PYTHON:-}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PYTHON="$(command -v python)"
    else
        echo "MISSING: python3 or python"
        exit 1
    fi
fi

if [[ ! -f "$REPORT_DIR/run_metadata.json" ]]; then
    echo "✗ no metadata for $REPORT_DIR — run bootstrap.sh first"
    exit 1
fi

echo "═══ security_scan.sh — tool=$TOOL_ID run=$RUN_ID ═══"

cd "$REPO_ROOT"

# ── 1. Mythos — internal scanner across 9 categories ────────────────
echo "→ Mythos (9 categories)…"
# Mythos is exposed via the live backend; we hit it through the API
# rather than re-importing in a host process. The HMAC key is derived
# inside the container by the actual `_derive_mythos_key()` function
# (HMAC-SHA512(MYTHOS_HMAC_SECRET, "mythos-nexusforge-admin-2026")[:64])
# — shelling out to the container avoids drift if the derivation algo
# changes.
MYTHOS_KEY=$(docker exec nexusforge_verify-backend-1 python -c \
    "from app.security.mythos import _derive_mythos_key; print(_derive_mythos_key())" \
    2>/dev/null | tr -d '\r\n')
if [[ -z "$MYTHOS_KEY" ]]; then
    echo "  ! could not derive Mythos key — emitting empty findings"
    echo '{"error":"mythos key derivation failed","findings":[]}' > "$RAW_DIR/mythos.json"
else
    curl -fsS -X POST -H "X-Mythos-Key: $MYTHOS_KEY" \
        http://localhost:18000/api/mythos/scan \
        > "$RAW_DIR/mythos.json" 2>/dev/null \
        || echo '{"error":"mythos endpoint unavailable","findings":[]}' > "$RAW_DIR/mythos.json"
fi

# ── 2. pip-audit — dep CVEs (Python) ────────────────────────────────
echo "→ pip-audit…"
"$PYTHON" -m pip_audit -r backend/requirements.txt --format=json \
    > "$RAW_DIR/pip_audit.json" 2>/dev/null \
    || echo '[]' > "$RAW_DIR/pip_audit.json"

# ── 3. npm audit — dep CVEs (frontend) ──────────────────────────────
echo "→ npm audit…"
( cd frontend && npm audit --json 2>/dev/null ) > "$RAW_DIR/npm_audit.json" \
    || echo '{"vulnerabilities":{}}' > "$RAW_DIR/npm_audit.json"

# ── 4. gitleaks — historical secrets in git ─────────────────────────
echo "→ gitleaks (full history)…"
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --no-banner --redact \
        --report-format=json --report-path="$RAW_DIR/gitleaks.json" \
        --source="$REPO_ROOT" 2>/dev/null \
        || true   # gitleaks exits non-zero if findings; that's expected
else
    echo "  (gitleaks not installed — emitting empty findings)"
    echo '[]' > "$RAW_DIR/gitleaks.json"
fi

# ── 5. semgrep — SAST rulesets ──────────────────────────────────────
echo "→ semgrep (auto config + p/security-audit)…"
if command -v semgrep >/dev/null 2>&1; then
    semgrep --config=p/security-audit --config=p/secrets \
        --json --quiet \
        --exclude=node_modules --exclude=.venv --exclude=verification \
        --output="$RAW_DIR/semgrep.json" \
        "$REPO_ROOT" 2>/dev/null \
        || true
else
    echo "  (semgrep not installed — emitting empty findings)"
    echo '{"results":[]}' > "$RAW_DIR/semgrep.json"
fi

# ── 6. schemathesis — API contract / fuzz against live backend ──────
echo "→ schemathesis (OpenAPI fuzz)…"
if command -v schemathesis >/dev/null 2>&1; then
    schemathesis run \
        --checks=all \
        --report-html=/dev/null \
        --hypothesis-max-examples=20 \
        --output="$RAW_DIR/schemathesis.json" \
        --no-color \
        http://localhost:18000/api/openapi.json 2>&1 | tail -20 \
        > "$RAW_DIR/schemathesis_log.txt" || true
fi
[[ -f "$RAW_DIR/schemathesis.json" ]] || echo '[]' > "$RAW_DIR/schemathesis.json"

# ── 7. Normalize + merge into findings.json ─────────────────────────
echo "→ Merging into normalized findings.json…"
"$PYTHON" "$REPO_ROOT/verification/_normalize_findings.py" \
    --raw-dir "$RAW_DIR" \
    --tool-id "$TOOL_ID" \
    --run-id "$RUN_ID" \
    --output "$REPORT_DIR/security_findings.json"

COUNT=$("$PYTHON" -c "
import json
data = json.load(open('$REPORT_DIR/security_findings.json'))
print(len(data['findings']))
")
echo "✓ Wrote $COUNT findings → $REPORT_DIR/security_findings.json"
