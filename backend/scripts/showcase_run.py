"""Showcase runner — end-to-end pipeline on a synthetic tenant.

Runs ingestion + csharp_analyzer + multi_lang_scanner across every app
under a tenant's synth_output/ directory and emits:
  - JSON report (machine-readable) at synth_output/<tenant>/showcase_report.json
  - Markdown report (human-readable) at synth_output/<tenant>/showcase_report.md

The report is the input the /executive dashboard will later consume and
the artefact used to demonstrate the "weeks not years" value prop.

USAGE:
    python backend/scripts/showcase_run.py                         # default tenant-alpha
    python backend/scripts/showcase_run.py --tenant tenant-alpha
    python backend/scripts/showcase_run.py --output-dir ./reports
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Allow running the script with `python backend/scripts/showcase_run.py`
# by adjusting sys.path.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.refactor.csharp_analyzer import CSharpAnalyzer  # noqa: E402
from app.refactor.ingestion import RepoIngestionEngine  # noqa: E402
from app.refactor.multi_lang_scanner import MultiLangScanner  # noqa: E402


SEVERITY_WEIGHTS = {"critical": 10, "high": 5, "medium": 2, "low": 1}


@dataclass
class AppReport:
    codename: str
    path: str
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    findings_by_category: dict[str, int] = field(default_factory=dict)
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    csharp_findings: int = 0
    multilang_findings: int = 0
    ingest_ms: int = 0
    analyze_ms: int = 0

    @property
    def total_findings(self) -> int:
        return self.csharp_findings + self.multilang_findings

    @property
    def risk_score(self) -> int:
        """Weighted risk: critical*10 + high*5 + medium*2 + low*1."""
        return sum(
            SEVERITY_WEIGHTS.get(sev, 0) * count
            for sev, count in self.findings_by_severity.items()
        )

    def to_dict(self) -> dict:
        return {
            "codename": self.codename,
            "path": self.path,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "findings": {
                "total": self.total_findings,
                "csharp_analyzer": self.csharp_findings,
                "multi_lang_scanner": self.multilang_findings,
                "by_category": self.findings_by_category,
                "by_severity": self.findings_by_severity,
            },
            "risk_score": self.risk_score,
            "timing": {
                "ingest_ms": self.ingest_ms,
                "analyze_ms": self.analyze_ms,
            },
        }


@dataclass
class TenantReport:
    tenant_id: str
    generated_at: str = ""
    apps: list[AppReport] = field(default_factory=list)
    total_duration_ms: int = 0

    @property
    def total_files(self) -> int:
        return sum(a.total_files for a in self.apps)

    @property
    def total_lines(self) -> int:
        return sum(a.total_lines for a in self.apps)

    @property
    def total_findings(self) -> int:
        return sum(a.total_findings for a in self.apps)

    @property
    def total_risk_score(self) -> int:
        return sum(a.risk_score for a in self.apps)

    @property
    def findings_by_category(self) -> dict[str, int]:
        agg: dict[str, int] = {}
        for app in self.apps:
            for cat, count in app.findings_by_category.items():
                agg[cat] = agg.get(cat, 0) + count
        return agg

    @property
    def findings_by_severity(self) -> dict[str, int]:
        agg: dict[str, int] = {}
        for app in self.apps:
            for sev, count in app.findings_by_severity.items():
                agg[sev] = agg.get(sev, 0) + count
        return agg

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "generated_at": self.generated_at,
            "totals": {
                "apps": len(self.apps),
                "files": self.total_files,
                "lines_of_code": self.total_lines,
                "findings": self.total_findings,
                "risk_score": self.total_risk_score,
                "findings_by_category": self.findings_by_category,
                "findings_by_severity": self.findings_by_severity,
            },
            "apps": [a.to_dict() for a in self.apps],
            "duration_ms": self.total_duration_ms,
        }


async def _scan_app(app_path: Path, codename: str) -> AppReport:
    report = AppReport(codename=codename, path=str(app_path))

    # 1) Ingestion
    t0 = time.monotonic()
    graph = await RepoIngestionEngine().ingest(str(app_path), codename)
    report.ingest_ms = int((time.monotonic() - t0) * 1000)
    report.total_files = graph.total_files
    report.total_lines = graph.total_lines
    report.languages = dict(graph.languages)

    # 2) C# analyzer
    t1 = time.monotonic()
    try:
        projects = await CSharpAnalyzer(str(app_path)).analyze()
        for p in projects:
            for f in p.findings:
                report.csharp_findings += 1
                report.findings_by_category[f.category] = (
                    report.findings_by_category.get(f.category, 0) + 1
                )
                report.findings_by_severity[f.severity] = (
                    report.findings_by_severity.get(f.severity, 0) + 1
                )
    except Exception:
        pass

    # 3) Multi-lang scanner
    ml_report = MultiLangScanner(str(app_path)).scan()
    for lang_report in ml_report.languages.values():
        for f in lang_report.findings:
            report.multilang_findings += 1
            report.findings_by_category[f.category] = (
                report.findings_by_category.get(f.category, 0) + 1
            )
            report.findings_by_severity[f.severity] = (
                report.findings_by_severity.get(f.severity, 0) + 1
            )

    report.analyze_ms = int((time.monotonic() - t1) * 1000)
    return report


async def run(tenant_id: str, synth_root: Path) -> TenantReport:
    tenant_path = synth_root / tenant_id
    if not tenant_path.exists():
        raise FileNotFoundError(
            f"No synth output for tenant {tenant_id!r} at {tenant_path}. "
            f"Run: python -m app.synth.generator --fixture backend/app/synth/fixtures/{tenant_id}.yaml"
        )

    report = TenantReport(tenant_id=tenant_id)
    report.generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    start = time.monotonic()
    app_dirs = sorted(p for p in tenant_path.iterdir() if p.is_dir())
    for app_dir in app_dirs:
        app_report = await _scan_app(app_dir, app_dir.name)
        report.apps.append(app_report)

    report.total_duration_ms = int((time.monotonic() - start) * 1000)
    return report


def _format_markdown(report: TenantReport) -> str:
    sev_labels = {"critical": "🔴 Critical", "high": "🟠 High", "medium": "🟡 Medium", "low": "🟢 Low"}
    lines: list[str] = []
    lines.append(f"# Showcase Report — `{report.tenant_id}`")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Pipeline duration:** {report.total_duration_ms} ms")
    lines.append("")
    lines.append("## Tenant totals")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Apps | {len(report.apps)} |")
    lines.append(f"| Files ingested | {report.total_files:,} |")
    lines.append(f"| Lines of code | {report.total_lines:,} |")
    lines.append(f"| Findings detected | **{report.total_findings:,}** |")
    lines.append(f"| Weighted risk score | {report.total_risk_score:,} |")
    lines.append("")
    lines.append("## Findings by severity")
    lines.append("")
    for sev, label in sev_labels.items():
        count = report.findings_by_severity.get(sev, 0)
        lines.append(f"- {label}: **{count:,}**")
    lines.append("")
    lines.append("## Findings by category")
    lines.append("")
    for cat, count in sorted(
        report.findings_by_category.items(), key=lambda x: -x[1]
    ):
        lines.append(f"- `{cat}`: {count:,}")
    lines.append("")
    lines.append("## Per-app breakdown")
    lines.append("")
    lines.append(
        "| App | Files | LOC | Findings | Risk score | Ingest | Analyze |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for app in report.apps:
        lines.append(
            f"| `{app.codename}` | {app.total_files} | {app.total_lines:,} "
            f"| {app.total_findings:,} | {app.risk_score:,} "
            f"| {app.ingest_ms} ms | {app.analyze_ms} ms |"
        )
    lines.append("")
    lines.append("## Demo narrative")
    lines.append("")
    lines.append(
        f"NexusForge ingested **{report.total_files:,} files** across "
        f"**{len(report.apps)} legacy applications** "
        f"(**{report.total_lines:,} LOC**), ran C# and multi-language "
        f"vulnerability scanners, and surfaced **{report.total_findings:,} findings** "
        f"in **{report.total_duration_ms / 1000:.2f} seconds**. "
        f"Manual discovery of the same codebase typically takes **months**. "
        f"NexusForge delivers it in **seconds**."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant",
        default="tenant-alpha",
        help="Tenant id (matches the directory under synth_output/)",
    )
    parser.add_argument(
        "--synth-root",
        default=str(REPO_ROOT / "synth_output"),
        help="Root directory containing tenant subdirs",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-app progress output",
    )
    args = parser.parse_args()

    synth_root = Path(args.synth_root).resolve()
    print(f"\nShowcase pipeline -> tenant={args.tenant} root={synth_root}")

    try:
        report = asyncio.run(run(args.tenant, synth_root))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Write reports next to the tenant synth output
    tenant_out = synth_root / args.tenant
    json_path = tenant_out / "showcase_report.json"
    md_path = tenant_out / "showcase_report.md"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2), encoding="utf-8"
    )
    md_path.write_text(_format_markdown(report), encoding="utf-8")

    # Console summary
    print()
    print("=" * 60)
    print(f"Showcase pipeline completed for {args.tenant}")
    print("=" * 60)
    print(f"Apps:         {len(report.apps)}")
    print(f"Files:        {report.total_files:,}")
    print(f"Lines:        {report.total_lines:,}")
    print(f"Findings:     {report.total_findings:,}")
    print(f"Risk score:   {report.total_risk_score:,}")
    print(f"Duration:     {report.total_duration_ms} ms")
    print()
    print(f"Reports written:")
    print(f"  {json_path}")
    print(f"  {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
