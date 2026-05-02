#!/usr/bin/env bash
# Local LLM triangulation node — runs ONE model with ONE focus over the
# existing automated findings. Sequential by design: a 6 GB VRAM laptop
# only holds one 8B model at a time, so multi-LLM = invocation in series.
#
# Three suggested combinations (each is its own tool_id in the
# triangulator):
#
#   bash verification/local_llm_review.sh deepseek_local deepseek-r1:8b   <run_id> security
#   bash verification/local_llm_review.sh qwen_local     qwen3.6:8b        <run_id> technical
#   bash verification/local_llm_review.sh llama_local    llama3.1:8b       <run_id> functional
#
# Each call swaps the model in Ollama (auto), evaluates the relevant
# findings (security_findings.json or functionality_findings.json from
# the same <run_id>), and writes:
#   verification/reports/<tool_id>/<run_id>/manual_findings_<focus>.json
#   verification/reports/<tool_id>/<run_id>/local_review_<focus>.md
#
# These auto-feed the triangulator the same as cloud-LLM nodes do.
#
# Usage:
#   bash verification/local_llm_review.sh <tool_id> <model> <run_id> <focus>
#
# Optional env:
#   OLLAMA_URL  — default http://localhost:11434 (the host's Ollama,
#                 NOT the docker stack's; the verify-stack ollama is now
#                 behind a `with-ollama` profile so it doesn't compete
#                 for VRAM with whatever you're running on the host)
#   MAX_FINDINGS — default 50 (cap to keep one pass under ~30 min)
set -euo pipefail

TOOL_ID="${1:?usage: $0 <tool_id> <model> <run_id> <focus>}"
MODEL="${2:?usage: $0 <tool_id> <model> <run_id> <focus>}"
RUN_ID="${3:?usage: $0 <tool_id> <model> <run_id> <focus>}"
FOCUS="${4:?usage: $0 <tool_id> <model> <run_id> <focus>}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MAX_FINDINGS="${MAX_FINDINGS:-50}"

case "$FOCUS" in
    security|technical|functional) ;;
    *) echo "✗ focus must be: security | technical | functional"; exit 1 ;;
esac

echo "═══ local_llm_review.sh — tool=$TOOL_ID model=$MODEL focus=$FOCUS ═══"

# ── 1. Quick health check on Ollama ─────────────────────────────────
if ! curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    echo "✗ Ollama not reachable at $OLLAMA_URL"
    echo "  start it: ollama serve   (or: systemctl --user start ollama)"
    exit 1
fi

# ── 2. Confirm the model is available locally ──────────────────────
if ! curl -fsS "$OLLAMA_URL/api/tags" | grep -q "\"name\":\"${MODEL}\""; then
    echo "  ! model $MODEL not found locally — pulling…"
    ollama pull "$MODEL" || {
        echo "✗ pull failed"
        exit 1
    }
fi

# ── 3. Run the Python runner ────────────────────────────────────────
python3 "$REPO_ROOT/verification/_local_llm_runner.py" \
    --tool-id "$TOOL_ID" \
    --run-id "$RUN_ID" \
    --model "$MODEL" \
    --focus "$FOCUS" \
    --ollama-url "$OLLAMA_URL" \
    --max-findings "$MAX_FINDINGS" \
    --repo-root "$REPO_ROOT"
