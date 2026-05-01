#!/usr/bin/env bash
# Triangulation bootstrap — bring up an isolated stack and ensure all
# tools the security/functionality scans need are installed.
#
# Idempotent: safe to re-run. Always restarts the stack from a clean
# state (volumes wiped) so verification is deterministic.
#
# Usage:
#   bash verification/bootstrap.sh [tool_id]
#
# `tool_id` is one of: aios | gpt55 | claude_security  (defaults to "claude_security").
# It only affects which subdir under verification/reports/ the run lands.
set -euo pipefail

TOOL_ID="${1:-claude_security}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$REPO_ROOT/verification/reports/$TOOL_ID/$RUN_ID"
mkdir -p "$REPORT_DIR"

echo "═══════════════════════════════════════════════════════"
echo "  Triangulation bootstrap"
echo "  tool   = $TOOL_ID"
echo "  run_id = $RUN_ID"
echo "  reports → $REPORT_DIR"
echo "═══════════════════════════════════════════════════════"

# ── 0. Sanity ───────────────────────────────────────────────────────
need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING: $1 — install before continuing"; exit 1; }; }
need docker
need python3

# Compose v2 lives under `docker compose` (subcommand), not the legacy
# `docker-compose` standalone binary. Detect either.
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "MISSING: docker compose (v2 plugin) or docker-compose (legacy)"
    exit 1
fi

# ── 1. Verification env file ────────────────────────────────────────
if [[ ! -f "$REPO_ROOT/.env.verify" ]]; then
    echo "→ .env.verify not found. Generating from env.verify.example with fresh secrets…"
    cp "$REPO_ROOT/env.verify.example" "$REPO_ROOT/.env.verify"
    JWT="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
    FERNET="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || echo 'GENERATE_MANUALLY')"
    # Use sed -i with backup ext for cross-platform safety (Linux GNU sed
    # accepts empty ext; macOS sed needs a literal ''). The .bak gets
    # cleaned at the end.
    sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$JWT|; \
                s|^JWT_SIGNING_SECRET=.*|JWT_SIGNING_SECRET=$JWT|; \
                s|^MYTHOS_HMAC_SECRET=.*|MYTHOS_HMAC_SECRET=$JWT|; \
                s|^FERNET_KEY=.*|FERNET_KEY=$FERNET|" "$REPO_ROOT/.env.verify"
    rm -f "$REPO_ROOT/.env.verify.bak"
    echo "  ✓ secrets generated. Add ANTHROPIC_API_KEY / GROQ / etc. by hand if needed."
fi

# ── 2. Tear down previous verification stack ────────────────────────
echo "→ Tearing down any previous verify stack (volumes too)…"
$DC -f "$REPO_ROOT/docker-compose.verify.yml" -p nexusforge_verify down -v --remove-orphans 2>&1 | tail -5

# ── 3. Build & bring up ──────────────────────────────────────────────
echo "→ Building images and bringing up stack (waits for health)…"
$DC -f "$REPO_ROOT/docker-compose.verify.yml" -p nexusforge_verify up -d --build --wait 2>&1 | tail -20

# ── 4. Smoke check the stack ────────────────────────────────────────
echo "→ Smoke checking the live stack…"
sleep 2
HEALTH=$(curl -fsS http://localhost:18000/api/health || echo "FAIL")
if [[ "$HEALTH" == "FAIL" ]]; then
    echo "✗ backend /api/health did not respond. Stack logs:"
    $DC -f "$REPO_ROOT/docker-compose.verify.yml" -p nexusforge_verify logs --tail=30 backend
    exit 1
fi
echo "  ✓ backend healthy: $HEALTH"

# ── 5. Install Python-side scanners (idempotent) ────────────────────
echo "→ Installing scanner dependencies (pip user install)…"
python3 -m pip install --quiet --user --upgrade \
    pip-audit \
    semgrep \
    schemathesis \
    httpx 2>&1 | tail -3

# ── 6. Install host-side scanners ───────────────────────────────────
# gitleaks is the reference secret scanner. Install via apt where
# available, otherwise via the upstream binary.
if ! command -v gitleaks >/dev/null 2>&1; then
    echo "→ Installing gitleaks…"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y -qq gitleaks 2>/dev/null || {
            echo "  apt install failed — falling back to binary download"
            GITLEAKS_VER="8.21.2"
            curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VER}/gitleaks_${GITLEAKS_VER}_linux_x64.tar.gz" \
                | tar -xzC /tmp gitleaks
            sudo install -m0755 /tmp/gitleaks /usr/local/bin/gitleaks
        }
    fi
fi

# trivy for container scans (optional — heavy, only if user opts in
# via TRIVY=1 env var)
if [[ "${TRIVY:-0}" == "1" ]] && ! command -v trivy >/dev/null 2>&1; then
    echo "→ Installing trivy (container scanner)…"
    sudo apt-get install -y -qq wget apt-transport-https gnupg
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" \
        | sudo tee -a /etc/apt/sources.list.d/trivy.list >/dev/null
    sudo apt-get update -qq && sudo apt-get install -y -qq trivy
fi

# ── 7. Persist run metadata ─────────────────────────────────────────
cat >"$REPORT_DIR/run_metadata.json" <<EOF
{
  "tool_id": "$TOOL_ID",
  "run_id": "$RUN_ID",
  "started_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_commit": "$(cd "$REPO_ROOT" && git rev-parse HEAD)",
  "git_branch": "$(cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD)",
  "stack_endpoints": {
    "backend": "http://localhost:18000",
    "frontend": "http://localhost:15173",
    "postgres": "postgres://nexus:nexus_verify_2026@localhost:15432/nexusforge_verify",
    "redis": "redis://localhost:16379",
    "mongodb": "mongodb://localhost:27018/nexusforge_verify",
    "ollama": "http://localhost:11435"
  },
  "report_dir": "$REPORT_DIR"
}
EOF

echo
echo "✓ Bootstrap done. Report dir: $REPORT_DIR"
echo
echo "Next:"
echo "  1. bash verification/security_scan.sh $TOOL_ID $RUN_ID"
echo "  2. bash verification/functionality_smoke.sh $TOOL_ID $RUN_ID"
echo "  3. (after all 3 tools have run) python3 verification/triangulate.py"
