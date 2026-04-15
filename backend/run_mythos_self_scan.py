"""Calibrated Mythos self-scan of the NexusForge platform.

Invokes MythosScanner with profile-aware priors reflecting NexusForge's
own mitigations:

- Baseline: app/security/baselines/nexusforge-self-scan-baseline.yaml
- Exposure: public-internet (Render backend + Vercel frontend)
- SecretManagement: env-vars + Fernet at rest (no Vault)
- EdgeSecurity: no WAF — Render / Vercel edge only

Run from the backend/ directory:

    python run_mythos_self_scan.py

Writes findings to /tmp/mythos-nexusforge-<timestamp>.json and prints a
human-readable triage summary to stdout.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force stdout to utf-8 on Windows so arrows / unicode don't crash the
# cp1252 console. Must happen before any print().
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from app.security.baseline_calibration import BaselineCalibration  # noqa: E402
from app.security.mythos import MythosScanner  # noqa: E402
from app.synth.profile import (  # noqa: E402
    EdgeSecurity,
    ExposureProfile,
    SecretManagement,
)


def _project_root() -> Path:
    # backend/ is one level below the project root
    return Path(__file__).parent.parent


def _load_baseline() -> BaselineCalibration:
    path = Path(__file__).parent / "app" / "security" / "baselines" / "nexusforge-self-scan-baseline.yaml"
    return BaselineCalibration(path)


def _build_profile_priors() -> tuple[ExposureProfile, EdgeSecurity, SecretManagement]:
    """Prior facts about NexusForge's deployment so the scanner does not
    re-flag known design decisions as findings."""

    exposure = ExposureProfile(
        surface="public-internet",           # Render + Vercel are public
        dual_backend=False,
        auth_layers=["jwt", "oauth"],        # Google OAuth + JWT middleware
        edge_protection="none",              # no corporate WAF; Vercel/Render edge only
        geo_restrictions=[],
        user_count=0,                        # public product
        mfa_required=False,                  # Google OAuth optionally enforces 2FA
    )

    edge = EdgeSecurity(
        waf_present=False,
        waf_provider="none",
        geo_blocking=[],
        pattern_rules=[],
        scan_cadence="on-demand",
        remediation_channel="github-prs",
    )

    secrets = SecretManagement(
        product="env-vars",                  # Render env-var injection
        internal_alias="",
        scope="per-app",
        rotation_policy="manual",
        hash_based_injection=False,
        on_premise=False,
        rotates_users=True,                  # JWT_SECRET rotation manual
        rotates_db_creds=False,
    )
    return exposure, edge, secrets


def _severity_rank(s: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(s, 5)


def _print_report(report, stats: dict, duration_ms: int) -> None:
    by_sev = report.to_dict()["by_severity"]
    by_cat = report.to_dict()["by_category"]

    print("=" * 70)
    print("MYTHOS SELF-SCAN — NEXUSFORGE")
    print("=" * 70)
    print(f"Duration:           {duration_ms:,} ms")
    print(f"Scanned files:      {report.scanned_files:,}")
    print(f"Scanned endpoints:  {report.scanned_endpoints}")
    print(f"Total findings:     {len(report.findings)}")
    print()
    print("By severity:")
    for sev in ("critical", "high", "medium", "low", "info"):
        if sev in by_sev:
            print(f"  {sev:10s} {by_sev[sev]:>5d}")
    print()
    print("By category:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat:12s} {count:>5d}")

    print()
    print("Baseline calibration stats:")
    for k, v in stats.items():
        print(f"  {k:20s} {v:>5d}")

    print()
    print("Top 20 findings (sorted by severity, then category):")
    print("-" * 70)
    sorted_findings = sorted(
        report.findings,
        key=lambda f: (_severity_rank(f.severity), f.category, f.title),
    )
    def _clean(s: str) -> str:
        # Normalize arrows + NBSP to ASCII so the console never crashes
        return (s or "").replace("\u2192", "->").replace("\u2190", "<-").replace("\u00a0", " ")

    for idx, f in enumerate(sorted_findings[:20], 1):
        where = f"{f.file_path}:{f.line_number}" if f.file_path else "(no file)"
        cwe = f" [{f.cwe}]" if f.cwe else ""
        print(f"{idx:2d}. [{f.severity:8s}] [{f.category:10s}]{cwe} {_clean(f.title)}")
        if f.description:
            print(f"       {_clean(f.description)[:180]}")
        if f.file_path:
            print(f"       where: {where}")
    if len(sorted_findings) > 20:
        print(f"\n... and {len(sorted_findings) - 20} more (see JSON output)")


async def main() -> None:
    root = _project_root()
    print(f"Scan root: {root}")

    baseline = _load_baseline()
    print(f"Baseline loaded: {baseline.is_loaded()} (mitigations: {list(baseline.mitigations.keys())})")

    exposure, edge, secrets = _build_profile_priors()

    scanner = MythosScanner(
        str(root),
        tenant_app="nexusforge",
        baseline=baseline,
        exposure=exposure,
        edge_security=edge,
        secret_management=secrets,
    )

    t0 = time.monotonic()
    report = await scanner.full_scan()
    duration_ms = int((time.monotonic() - t0) * 1000)

    _print_report(report, scanner.calibration_stats, duration_ms)

    # Write JSON
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path("/tmp") / f"mythos-nexusforge-{ts}.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "scan_root": str(root),
                    "duration_ms": duration_ms,
                    "calibration_stats": scanner.calibration_stats,
                    "baseline_summary": baseline.summary(),
                    "report": report.to_dict(),
                },
                fh, indent=2, ensure_ascii=False,
            )
        print(f"\nFull JSON report: {out}")
    except OSError as exc:  # pragma: no cover
        print(f"\n(warning) could not write JSON report: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
