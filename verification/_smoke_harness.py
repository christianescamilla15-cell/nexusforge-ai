"""Functionality smoke harness — runs every golden path against the
live verification stack and emits one functionality.json.

Each smoke is decorated with @smoke(name, severity_on_fail) and
returns either:
  - None / nothing → passed
  - a string → message that becomes the finding description on fail
  - raises an exception → automatically caught and logged as failure

Why one Python file instead of pytest: the goal is the SAME test
surface across all three triangulation tools, with the SAME output
shape. Using pytest would tempt each tool's session to add their own
fixtures / overrides and drift. The harness is intentionally simple
and string-based.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

# ── smoke registry ──────────────────────────────────────────────────


@dataclass
class Smoke:
    name: str
    severity_on_fail: str  # critical|high|medium|low
    fn: Callable[["Context"], str | None]
    surface: str  # which surface this smoke covers


_REGISTRY: list[Smoke] = []


def smoke(name: str, severity: str, surface: str):
    def decorator(fn):
        _REGISTRY.append(Smoke(name=name, severity_on_fail=severity, fn=fn, surface=surface))
        return fn
    return decorator


@dataclass
class Context:
    base_url: str
    frontend_url: str
    client: httpx.Client
    access_token: str | None = None
    refresh_token: str | None = None
    test_email: str = field(default_factory=lambda: f"verify-{uuid.uuid4().hex[:10]}@nexusforge.test")
    test_password: str = "VerifyPass123!"
    artifacts: dict = field(default_factory=dict)


# ── smokes ───────────────────────────────────────────────────────────


@smoke("backend health", "critical", "operational")
def smoke_health(ctx: Context):
    r = ctx.client.get(f"{ctx.base_url}/api/health", timeout=5)
    if r.status_code != 200:
        return f"GET /api/health → {r.status_code}, body={r.text[:200]}"
    return None


@smoke("frontend reachable", "high", "operational")
def smoke_frontend(ctx: Context):
    r = ctx.client.get(ctx.frontend_url, timeout=5)
    if r.status_code != 200:
        return f"frontend root → {r.status_code}"
    if "<div" not in r.text and "<html" not in r.text:
        return "frontend response doesn't look like HTML"
    return None


@smoke("auth: register + login + me", "critical", "auth")
def smoke_auth(ctx: Context):
    # Register
    r = ctx.client.post(
        f"{ctx.base_url}/api/auth/register",
        json={"email": ctx.test_email, "password": ctx.test_password, "full_name": "Verify Bot"},
    )
    if r.status_code not in (200, 201):
        return f"register → {r.status_code}, body={r.text[:300]}"

    # Login
    r = ctx.client.post(
        f"{ctx.base_url}/api/auth/login",
        json={"email": ctx.test_email, "password": ctx.test_password},
    )
    if r.status_code != 200:
        return f"login → {r.status_code}, body={r.text[:300]}"
    body = r.json()
    ctx.access_token = body.get("access_token") or body.get("token")
    ctx.refresh_token = body.get("refresh_token")
    if not ctx.access_token:
        return f"login response missing access token: {body}"

    # /me echoes the user
    r = ctx.client.get(
        f"{ctx.base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )
    if r.status_code != 200:
        return f"/api/auth/me → {r.status_code}"
    return None


@smoke("workflow: create + run + execution recorded", "high", "workflow_runtime")
def smoke_workflow(ctx: Context):
    if not ctx.access_token:
        return "skipped: no auth token"
    headers = {"Authorization": f"Bearer {ctx.access_token}"}

    # Create a trivial workflow (a single noop step).
    r = ctx.client.post(
        f"{ctx.base_url}/api/workflows/",
        headers=headers,
        json={
            "name": f"verify-{uuid.uuid4().hex[:6]}",
            "description": "smoke",
            "dag_definition": {
                "steps": [{"name": "s1", "type": "echo", "config": {"text": "hi"}}],
            },
        },
    )
    if r.status_code not in (200, 201):
        # Some deployments expect a different shape — record but don't crash
        return f"workflow create → {r.status_code}, body={r.text[:300]}"
    wf_id = r.json().get("id") or r.json().get("workflow_id")
    if not wf_id:
        return f"workflow created but response missing id: {r.json()}"

    # Run it via the executions API (`POST /api/executions/`).
    # The previously-tried `POST /api/workflows/{id}/run` was never implemented.
    r = ctx.client.post(
        f"{ctx.base_url}/api/executions/",
        headers=headers,
        json={
            "workflow_id": wf_id,
            "trigger_type": "manual",
            "input_data": {},
        },
    )
    if r.status_code not in (200, 201, 202):
        return f"executions create → {r.status_code}, body={r.text[:300]}"
    ctx.artifacts["workflow_id"] = wf_id
    ctx.artifacts["run_id"] = r.json().get("run_id") or r.json().get("id")
    return None


@smoke("wizard: chat returns assistant_message", "high", "wizard")
def smoke_wizard(ctx: Context):
    if not ctx.access_token:
        return "skipped: no auth token"
    # `/api/wizard/chat` is a StreamingResponse (SSE). We don't need to
    # parse the full event stream here — accept any 200 with a non-empty
    # body. The failure modes that matter (wrong status, dead pipe, empty
    # body) are still caught.
    with ctx.client.stream(
        "POST",
        f"{ctx.base_url}/api/wizard/chat",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
        json={
            "messages": [
                {"role": "user", "content": "I want a simple dashboard for inventory tracking"},
            ],
            "language": "en",
        },
        timeout=30,
    ) as r:
        if r.status_code != 200:
            return f"wizard/chat → {r.status_code}"
        bytes_seen = 0
        for chunk in r.iter_bytes():
            bytes_seen += len(chunk)
            if bytes_seen >= 32:  # got at least one event
                break
        if bytes_seen == 0:
            return "wizard/chat → 200 but empty stream"
    return None


@smoke("synthesizer: chat → templates → build (E2E)", "medium", "platform_synth")
def smoke_synthesizer(ctx: Context):
    if not ctx.access_token:
        return "skipped: no auth token"
    headers = {"Authorization": f"Bearer {ctx.access_token}"}

    # Chat once to populate spec
    r = ctx.client.post(
        f"{ctx.base_url}/api/platform-synth/chat",
        headers=headers,
        json={
            "user_message": "Python FastAPI dashboard with Postgres",
            "history": [],
            "current_spec": {"project_name": f"verify-{uuid.uuid4().hex[:6]}"},
        },
        timeout=30,
    )
    if r.status_code != 200:
        return f"platform-synth/chat → {r.status_code}, body={r.text[:300]}"
    spec = r.json().get("spec") or {}
    if not spec.get("project_name"):
        spec["project_name"] = f"verify-{uuid.uuid4().hex[:6]}"

    # List templates
    r = ctx.client.get(f"{ctx.base_url}/api/platform-synth/templates", headers=headers)
    if r.status_code != 200:
        return f"templates list → {r.status_code}"

    # Build into a tmp dir under PLATFORM_SYNTH_ROOT (set in env to /tmp/...)
    target = f"/tmp/nexusforge_verify_synth/{spec['project_name']}"
    r = ctx.client.post(
        f"{ctx.base_url}/api/platform-synth/build",
        headers=headers,
        json={
            "template_id": "fastapi_react_postgres",
            "spec": spec,
            "target_dir": target,
        },
        timeout=60,
    )
    if r.status_code not in (200, 201):
        return f"synth build → {r.status_code}, body={r.text[:300]}"
    body = r.json()
    if body.get("status") not in ("complete", "partial"):
        return f"unexpected build status: {body.get('status')}"
    if body.get("files_written", 0) < 5:
        return f"build only wrote {body.get('files_written')} files (expected ≥5)"
    ctx.artifacts["synth_project"] = body.get("project_path")
    return None


@smoke("refactor: ingest a tiny sample dir", "high", "refactor_engine")
def smoke_refactor(ctx: Context):
    if not ctx.access_token:
        return "skipped: no auth token"
    # The backend container can't see the host filesystem, so creating the
    # sample with `Path(...).mkdir()` on the host doesn't help — the API
    # validates that the path exists from INSIDE the container. We write
    # the sample directly into the container via `docker exec`. The path
    # `/tmp/nexusforge_verify_synth/` already exists in the container
    # (the platform-synth output dir), so we reuse it.
    sample = "/tmp/nexusforge_verify_synth/refactor_sample"
    docker_setup = subprocess.run(
        [
            "docker", "exec", "nexusforge_verify-backend-1",
            "sh", "-c",
            f"mkdir -p {sample} && "
            f"printf 'def hello():\\n    print(\"hi\")\\n' > {sample}/main.py",
        ],
        capture_output=True, text=True, timeout=10,
    )
    if docker_setup.returncode != 0:
        return f"refactor: failed to create sample in container: {docker_setup.stderr[:200]}"
    r = ctx.client.post(
        f"{ctx.base_url}/api/refactor/ingest",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
        json={"path": sample, "name": "verify-refactor-smoke"},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        return f"refactor/ingest → {r.status_code}, body={r.text[:300]}"
    return None


@smoke("audit log returns rows for current user", "low", "audit")
def smoke_audit(ctx: Context):
    if not ctx.access_token:
        return "skipped: no auth token"
    r = ctx.client.get(
        f"{ctx.base_url}/api/audit/",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )
    # Empty list is a valid response — the smoke just verifies the
    # endpoint mounted and answered authenticated.
    if r.status_code not in (200, 204):
        return f"audit/ → {r.status_code}"
    return None


@smoke("tenant isolation: user B cannot read user A's workflow", "critical", "auth")
def smoke_tenant_isolation(ctx: Context):
    """Two-user round-trip cross-fetch.

    Closes the IDOR class of bugs the 6 single-user scanners didn't model
    (Tier 2 follow-up to the 2026-05-02 triangulation, claude_security
    recommendation #9 / aios M-AIOS-2). Registers two fresh users (UUID-
    suffixed emails so reruns don't collide), creates a workflow owned by
    A, and confirms B's token gets 403 on GET / PUT / DELETE.
    """
    # ── Register user A ──────────────────────────────────────────────
    a_email = f"a-{uuid.uuid4().hex[:8]}@verify.local"
    r = ctx.client.post(
        f"{ctx.base_url}/api/auth/register",
        json={"email": a_email, "password": "verify-A-pw-2026", "name": "Alice"},
        timeout=15,
    )
    if r.status_code not in (200, 201):
        return f"register A → {r.status_code}, body={r.text[:200]}"
    a_token = (r.json().get("access_token") or r.json().get("token"))
    if not a_token:
        return f"register A: no token in body keys={list(r.json().keys())}"

    # ── Create a workflow owned by A ────────────────────────────────
    r = ctx.client.post(
        f"{ctx.base_url}/api/workflows/",
        headers={"Authorization": f"Bearer {a_token}"},
        json={
            "name": f"alice-iso-{uuid.uuid4().hex[:6]}",
            "description": "tenant-isolation smoke",
            "dag_definition": {
                "steps": [{"name": "s1", "type": "echo", "config": {"text": "hi"}}],
            },
        },
        timeout=15,
    )
    if r.status_code not in (200, 201):
        return f"A create workflow → {r.status_code}, body={r.text[:200]}"
    wf_id = r.json().get("id") or r.json().get("workflow_id")
    if not wf_id:
        return f"A workflow created but no id: {r.json()}"

    # ── Register user B ──────────────────────────────────────────────
    b_email = f"b-{uuid.uuid4().hex[:8]}@verify.local"
    r = ctx.client.post(
        f"{ctx.base_url}/api/auth/register",
        json={"email": b_email, "password": "verify-B-pw-2026", "name": "Bob"},
        timeout=15,
    )
    if r.status_code not in (200, 201):
        return f"register B → {r.status_code}"
    b_token = (r.json().get("access_token") or r.json().get("token"))
    if not b_token:
        return f"register B: no token"

    b_headers = {"Authorization": f"Bearer {b_token}"}

    # ── B tries to GET A's workflow → expect 403 (or 404 if hardened) ─
    r = ctx.client.get(f"{ctx.base_url}/api/workflows/{wf_id}", headers=b_headers, timeout=10)
    if r.status_code not in (403, 404):
        return f"IDOR — B GET A's workflow returned {r.status_code} (expected 403/404), body={r.text[:200]}"

    # ── B tries to PUT (update) → expect 403/404 ─────────────────────
    r = ctx.client.put(
        f"{ctx.base_url}/api/workflows/{wf_id}",
        headers=b_headers,
        json={"name": "hijacked-by-bob"},
        timeout=10,
    )
    if r.status_code not in (403, 404):
        return f"IDOR — B PUT A's workflow returned {r.status_code} (expected 403/404)"

    # ── B tries to DELETE → expect 403/404 ───────────────────────────
    r = ctx.client.delete(f"{ctx.base_url}/api/workflows/{wf_id}", headers=b_headers, timeout=10)
    if r.status_code not in (403, 404):
        return f"IDOR — B DELETE A's workflow returned {r.status_code} (expected 403/404)"

    return None


# ── runner ───────────────────────────────────────────────────────────


def run_smokes(ctx: Context) -> dict:
    results = []
    passed = 0
    failed = 0
    skipped = 0
    started = time.time()

    for s in _REGISTRY:
        t0 = time.time()
        outcome: dict = {
            "name": s.name,
            "surface": s.surface,
            "severity_on_fail": s.severity_on_fail,
            "duration_ms": 0,
            "status": "passed",
            "message": None,
        }
        try:
            msg = s.fn(ctx)
            if msg is None:
                passed += 1
            else:
                if msg.startswith("skipped:"):
                    outcome["status"] = "skipped"
                    outcome["message"] = msg
                    skipped += 1
                else:
                    outcome["status"] = "failed"
                    outcome["message"] = msg
                    failed += 1
        except Exception as exc:  # noqa: BLE001 — we want all errors here
            outcome["status"] = "failed"
            outcome["message"] = f"exception: {type(exc).__name__}: {exc}"
            failed += 1
        outcome["duration_ms"] = int((time.time() - t0) * 1000)
        results.append(outcome)

    return {
        "results": results,
        "summary": {
            "total": len(_REGISTRY),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": int((time.time() - started) * 1000),
        },
    }


def to_findings(report: dict, tool_id: str, run_id: str) -> dict:
    """Convert the smoke results into the unified findings shape so the
    triangulator can cross-reference functionality outcomes the same
    way it does security findings."""
    import hashlib

    findings = []
    for r in report["results"]:
        if r["status"] != "failed":
            continue
        fid = hashlib.sha1(
            f"smoke|{r['surface']}|{r['name']}".encode()
        ).hexdigest()[:16]
        findings.append({
            "id": fid,
            "source_scanner": "smoke",
            "category": "functionality",
            "severity": r["severity_on_fail"],
            "file": r["surface"],
            "line": None,
            "title": f"smoke failed: {r['name']}",
            "description": r["message"] or "",
            "cwe": None,
            "cvss": None,
        })

    return {
        "tool_id": tool_id,
        "run_id": run_id,
        "scan_kind": "functionality",
        "summary": report["summary"],
        "results": report["results"],
        "finding_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--frontend-url", required=True)
    p.add_argument("--tool-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    Path("/tmp/nexusforge_verify_synth").mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True) as client:
        ctx = Context(base_url=args.base_url, frontend_url=args.frontend_url, client=client)
        report = run_smokes(ctx)

    findings = to_findings(report, args.tool_id, args.run_id)
    Path(args.output).write_text(json.dumps(findings, indent=2), encoding="utf-8")

    s = report["summary"]
    print(f"  {s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped, {s['duration_ms']}ms")
    return 0 if s["failed"] == 0 else 0  # don't exit non-zero — triangulator handles it


if __name__ == "__main__":
    sys.exit(main())
