#!/bin/bash
# Codex environment setup — runs before the agent starts.
# Installs Python deps so pytest, Mythos scanner, and discovery_loader work.

set -e

echo "=== Codex setup: installing backend dependencies ==="
cd backend

# Install core deps (skip heavy ML libs that aren't needed for audit)
pip install -q \
  fastapi \
  pydantic \
  pydantic-settings \
  PyYAML \
  openpyxl \
  pytest \
  pytest-asyncio \
  httpx \
  2>&1 | tail -3

echo "=== Codex setup: verifying key files exist ==="
for f in \
  app/refactor/discovery_loader.py \
  app/security/baseline_calibration.py \
  app/security/baselines/nexusforge-self-scan-baseline.yaml \
  app/synth/ecosystem_metrics.py \
  run_mythos_self_scan.py; do
  if [ -f "$f" ]; then
    echo "  ✓ $f"
  else
    echo "  ✗ MISSING: $f — clone may be stale!"
  fi
done

echo "=== Codex setup: done ==="
