"""End-to-end analysis script for client repos.

Run this when a new client app repo arrives. It chains:
1. Repo ingestion → ProjectGraph
2. C# analyzer (if .NET)
3. Mythos calibrated scan (with tenant-alpha baseline)
4. StranglerPlanner with all 3 priors (discovery + ecosystem + recipe)
5. JSON + Markdown report output

Usage:
    python run_client_repo_analysis.py <repo_path> <app_codename> [--output-dir /tmp/reports]

Example:
    python run_client_repo_analysis.py C:/tmp/noshow-robot/ATOS-NOSHOW-ROBOT noshow-robot
    python run_client_repo_analysis.py C:/repos/mi-refund-arc app-03-arc
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("client-analysis")

# Paths
BACKEND = Path(__file__).parent
CORPUS = Path("C:/Users/DANNY/NexusForge-Shared/transcripciones-generales")
TENANT_FIXTURE = BACKEND / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
BASELINE = BACKEND / "app" / "security" / "baselines" / "tenant-alpha-vulns-baseline.yaml"


async def run_analysis(
    repo_path: str,
    app_codename: str,
    output_dir: str = "/tmp/reports",
) -> dict:
    """Run the full analysis pipeline on a client repo."""
    results: dict = {
        "repo_path": repo_path,
        "app_codename": app_codename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": {},
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    t_total = time.monotonic()

    # ── Step 1: Repo Ingestion ──────────────────────────────────────
    logger.info("Step 1: Ingesting repo %s as %s", repo_path, app_codename)
    t0 = time.monotonic()
    try:
        from app.refactor.ingestion import RepoIngestionEngine
        engine = RepoIngestionEngine()
        graph = await engine.ingest(repo_path, app_codename)
        results["steps"]["ingestion"] = {
            "status": "ok",
            "total_files": graph.total_files,
            "total_lines": graph.total_lines,
            "languages": graph.languages,
            "modules": len(graph.modules),
            "duration_ms": int((time.monotonic() - t0) * 1000),
        }
        logger.info(
            "  Ingested: %d files, %d LOC, %d modules in %dms",
            graph.total_files, graph.total_lines, len(graph.modules),
            results["steps"]["ingestion"]["duration_ms"],
        )
    except Exception as exc:
        logger.error("  Ingestion failed: %s", exc)
        results["steps"]["ingestion"] = {"status": "failed", "error": str(exc)}
        graph = None

    # ── Step 2: C# Analysis (if .NET detected) ─────────────────────
    if graph and "csharp" in (graph.languages or {}):
        logger.info("Step 2: Running C# analyzer")
        t0 = time.monotonic()
        try:
            from app.refactor.csharp_analyzer import CSharpAnalyzer
            analyzer = CSharpAnalyzer(repo_path)
            projects = await analyzer.analyze()
            total_findings = sum(len(p.findings) for p in projects)
            total_classes = sum(len(p.classes) for p in projects)
            results["steps"]["csharp_analyzer"] = {
                "status": "ok",
                "projects": len(projects),
                "classes": total_classes,
                "findings": total_findings,
                "duration_ms": int((time.monotonic() - t0) * 1000),
            }
            logger.info(
                "  C# analysis: %d projects, %d classes, %d findings in %dms",
                len(projects), total_classes, total_findings,
                results["steps"]["csharp_analyzer"]["duration_ms"],
            )
        except Exception as exc:
            logger.error("  C# analyzer failed: %s", exc)
            results["steps"]["csharp_analyzer"] = {"status": "failed", "error": str(exc)}
    else:
        results["steps"]["csharp_analyzer"] = {"status": "skipped", "reason": "no C# detected"}

    # ── Step 3: StranglerPlanner with 3 priors ─────────────────────
    logger.info("Step 3: Running StranglerPlanner with priors")
    t0 = time.monotonic()
    try:
        from app.refactor.strangler_planner import build_plan, render_markdown

        plan = await build_plan(
            repo_path,
            name=app_codename,
            discovery_context_path=str(CORPUS) if CORPUS.is_dir() else None,
            load_default_ecosystem_metrics=True,
            tenant_profile_path=str(TENANT_FIXTURE) if TENANT_FIXTURE.is_file() else None,
            tenant_app_codename=app_codename,
        )

        plan_dict = plan.to_dict()
        plan_md = render_markdown(plan)

        results["steps"]["strangler_planner"] = {
            "status": "ok",
            "total_modules": plan.total_modules,
            "total_loc": plan.total_loc,
            "total_vulns": plan.total_vulns,
            "phases": len(plan.phases),
            "effort_days": plan.total_effort_days,
            "discovery_findings": plan.discovery_findings_count,
            "ecosystem_priority_score": plan.ecosystem_priority_score,
            "multi_robot_risk": plan.multi_robot_risk,
            "duration_ms": int((time.monotonic() - t0) * 1000),
        }

        # Write markdown plan
        md_path = out / f"{app_codename}-strangler-plan.md"
        md_path.write_text(plan_md, encoding="utf-8")
        logger.info(
            "  Plan: %d phases, %d effort-days, priority=%.1f, written to %s",
            len(plan.phases), plan.total_effort_days,
            plan.ecosystem_priority_score, md_path,
        )
    except Exception as exc:
        logger.error("  StranglerPlanner failed: %s", exc)
        results["steps"]["strangler_planner"] = {"status": "failed", "error": str(exc)}

    # ── Step 4: Manual security grep (since Mythos targets NexusForge structure) ──
    logger.info("Step 4: Security grep scan")
    t0 = time.monotonic()
    security_findings = []
    repo = Path(repo_path)
    try:
        # Credentials in config files
        for cfg in repo.rglob("*.config"):
            content = cfg.read_text(encoding="utf-8", errors="ignore")
            for keyword in ("password", "Password", "PASSPHRASE", "connectionString"):
                if keyword.lower() in content.lower():
                    for i, line in enumerate(content.splitlines(), 1):
                        if keyword.lower() in line.lower():
                            security_findings.append({
                                "severity": "critical",
                                "category": "secrets",
                                "title": f"Potential credential in {cfg.name}",
                                "file": str(cfg.relative_to(repo)),
                                "line": i,
                                "cwe": "CWE-798",
                            })

        # StackTrace leaks
        for cs in repo.rglob("*.cs"):
            if "packages" in str(cs) or "obj" in str(cs):
                continue
            content = cs.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if "StackTrace" in line or ("ex.Message" in line and "log" not in line.lower()):
                    security_findings.append({
                        "severity": "medium",
                        "category": "info_leak",
                        "title": "StackTrace or exception message exposed",
                        "file": str(cs.relative_to(repo)),
                        "line": i,
                        "cwe": "CWE-209",
                    })

        # Zero tests
        test_files = list(repo.rglob("*Test*.cs")) + list(repo.rglob("*test*.cs"))
        test_files = [f for f in test_files if "packages" not in str(f)]
        if not test_files:
            security_findings.append({
                "severity": "medium",
                "category": "quality",
                "title": "No test files detected (0% coverage)",
                "file": "",
                "line": 0,
            })

        results["steps"]["security_grep"] = {
            "status": "ok",
            "findings": len(security_findings),
            "by_severity": {},
            "duration_ms": int((time.monotonic() - t0) * 1000),
        }
        for f in security_findings:
            sev = f["severity"]
            results["steps"]["security_grep"]["by_severity"][sev] = \
                results["steps"]["security_grep"]["by_severity"].get(sev, 0) + 1

        logger.info(
            "  Security grep: %d findings in %dms",
            len(security_findings),
            results["steps"]["security_grep"]["duration_ms"],
        )
    except Exception as exc:
        logger.error("  Security grep failed: %s", exc)
        results["steps"]["security_grep"] = {"status": "failed", "error": str(exc)}

    # ── Finalize ───────────────────────────────────────────────────
    results["total_duration_ms"] = int((time.monotonic() - t_total) * 1000)
    results["security_findings"] = security_findings

    # Write JSON report
    json_path = out / f"{app_codename}-analysis.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    # Print summary
    print()
    print("=" * 60)
    print(f"ANALYSIS COMPLETE — {app_codename}")
    print("=" * 60)
    print(f"Duration: {results['total_duration_ms']}ms")
    for step_name, step_data in results["steps"].items():
        status = step_data.get("status", "?")
        icon = "✓" if status == "ok" else "✗" if status == "failed" else "—"
        detail = ""
        if "findings" in step_data:
            detail = f" ({step_data['findings']} findings)"
        elif "total_files" in step_data:
            detail = f" ({step_data['total_files']} files, {step_data.get('total_lines', 0)} LOC)"
        elif "phases" in step_data:
            detail = f" ({step_data['phases']} phases, {step_data.get('effort_days', 0)}d)"
        print(f"  {icon} {step_name}: {status}{detail}")

    if security_findings:
        print(f"\nSecurity findings: {len(security_findings)}")
        for sev in ("critical", "high", "medium", "low"):
            count = results["steps"].get("security_grep", {}).get("by_severity", {}).get(sev, 0)
            if count:
                print(f"  {sev}: {count}")

    print(f"\nReports: {json_path}")
    if (out / f"{app_codename}-strangler-plan.md").exists():
        print(f"         {out / f'{app_codename}-strangler-plan.md'}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze a client repo E2E")
    parser.add_argument("repo_path", help="Path to the extracted repo")
    parser.add_argument("app_codename", help="App codename (e.g., app-03-arc, noshow-robot)")
    parser.add_argument("--output-dir", default="C:/tmp/reports", help="Output directory")
    args = parser.parse_args()

    asyncio.run(run_analysis(args.repo_path, args.app_codename, args.output_dir))


if __name__ == "__main__":
    main()
