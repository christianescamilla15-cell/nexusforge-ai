"""Triangulator — given the latest run from each tool, computes
agreement scores and emits a consolidated report.

Why this is the actual value:
  - 1 source of truth flagged a thing → could be a false positive (each
    scanner has well-known noise modes)
  - 2/3 sources flagged → high signal — fix soon
  - 3/3 sources flagged → essentially certain — fix first

Findings are matched on a coarse identity (category + file + title-token
overlap), not the exact `id` hash, because each tool's scanner family
phrases the same vuln slightly differently. Two findings count as
"the same" when:
  - same category, AND
  - same file (or both file is None — for dep findings)
  - title shares ≥ 2 tokens (after lowercasing + stop-word strip)

Outputs:
  verification/reports/_triangulation/<run_ts>/triangulation.md
  verification/reports/_triangulation/<run_ts>/triangulation.json

Usage:
  python3 verification/triangulate.py
  python3 verification/triangulate.py --tools aios,gpt55,claude_security
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "verification" / "reports"

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "in", "on", "of", "for",
    "to", "and", "or", "but", "if", "with", "without", "by", "from",
    "smoke", "failed", "test", "check",
}


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    return {
        t for t in re.findall(r"[a-z0-9]{3,}", text.lower())
        if t not in STOP_WORDS
    }


def _latest_report(tool_id: str, kind: str) -> dict | None:
    """Find the most-recent run for a given tool and load its findings."""
    base = REPORTS_DIR / tool_id
    if not base.is_dir():
        return None
    runs = sorted([p for p in base.iterdir() if p.is_dir()], reverse=True)
    for run in runs:
        rpt = run / f"{kind}_findings.json"
        if rpt.exists():
            try:
                return json.loads(rpt.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return None


def _equivalent(a: dict, b: dict) -> bool:
    """Coarse equality: do these findings probably describe the same thing?"""
    if a.get("category") != b.get("category"):
        return False
    fa = a.get("file") or ""
    fb = b.get("file") or ""
    # Allow file mismatch only when both are None/empty (dep CVEs etc).
    if fa or fb:
        if Path(fa).name != Path(fb).name:
            return False
    overlap = _tokens(a.get("title", "")) & _tokens(b.get("title", ""))
    return len(overlap) >= 2


def cluster_findings(per_tool: dict[str, list[dict]]) -> list[dict]:
    """Group equivalent findings across tools. Returns clusters with
    `agreement` = number of tools that flagged it."""
    clusters: list[dict] = []

    flat = []
    for tool, findings in per_tool.items():
        for f in findings:
            flat.append((tool, f))

    used = [False] * len(flat)
    for i, (tool_i, f_i) in enumerate(flat):
        if used[i]:
            continue
        cluster_finds: list[tuple[str, dict]] = [(tool_i, f_i)]
        used[i] = True
        for j in range(i + 1, len(flat)):
            if used[j]:
                continue
            tool_j, f_j = flat[j]
            if _equivalent(f_i, f_j):
                cluster_finds.append((tool_j, f_j))
                used[j] = True
        sources = sorted({t for t, _ in cluster_finds})
        # Severity = max severity reported by any source
        severity_order = ["info", "low", "medium", "high", "critical"]
        max_sev = max(
            (severity_order.index(f.get("severity", "info")) for _, f in cluster_finds),
            default=0,
        )
        clusters.append({
            "agreement": len(sources),
            "sources": sources,
            "category": f_i.get("category"),
            "severity": severity_order[max_sev],
            "file": f_i.get("file"),
            "line": f_i.get("line"),
            "title": f_i.get("title"),
            "descriptions_by_tool": {
                t: f.get("description", "") for t, f in cluster_finds
            },
        })

    clusters.sort(
        key=lambda c: (
            -c["agreement"],
            -["info", "low", "medium", "high", "critical"].index(c["severity"]),
        )
    )
    return clusters


def build_markdown(clusters: list[dict], summary: dict) -> str:
    lines = [
        "# Triangulation report",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "## Summary",
        "",
        f"- Tools cross-referenced: **{summary['tools_count']}** ({', '.join(summary['tools'])})",
        f"- Total findings raised: **{summary['total_raw_findings']}**",
        f"- Distinct issue clusters after dedup: **{summary['cluster_count']}**",
        f"  - 3/3 sources agree (HIGH-CONFIDENCE): **{summary['agreement_3']}**",
        f"  - 2/3 sources agree: **{summary['agreement_2']}**",
        f"  - Single-source (investigate): **{summary['agreement_1']}**",
        "",
        "## Triage order",
        "",
        "Fix order: agreement DESC, then severity DESC. Single-source",
        "items at the bottom are candidates for false-positive review.",
        "",
    ]

    by_agreement = defaultdict(list)
    for c in clusters:
        by_agreement[c["agreement"]].append(c)

    for agree in sorted(by_agreement.keys(), reverse=True):
        bucket = by_agreement[agree]
        if not bucket:
            continue
        label = (
            "HIGH-CONFIDENCE (3/3)" if agree >= 3
            else f"{agree}/3 — needs investigation" if agree == 1
            else f"{agree}/3 — likely real"
        )
        lines.append(f"### {label}")
        lines.append("")
        for c in bucket:
            sev = c["severity"].upper()
            file = c["file"] or "-"
            line = f":{c['line']}" if c.get("line") else ""
            lines.append(f"- **[{sev}]** [{c['category']}] `{file}{line}` — {c['title']}")
            lines.append(f"   - sources: {', '.join(c['sources'])}")
            for tool, desc in c["descriptions_by_tool"].items():
                if desc:
                    one = desc.replace("\n", " ").strip()[:200]
                    lines.append(f"   - {tool}: {one}")
            lines.append("")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--tools",
        default="claude_security,gpt55,aios,deepseek_local,qwen_local,llama_local",
        help="Comma-separated tool ids to triangulate. Canonical 6-source flow includes "
             "the two cloud nodes (claude_security, gpt55), the AIOS persistent-memory "
             "node, and the three local Ollama nodes (deepseek/qwen/llama). Override "
             "to a subset for partial passes.",
    )
    p.add_argument(
        "--kinds",
        default="security,functionality",
        help="Which finding kinds to merge (security|functionality|both)",
    )
    args = p.parse_args()

    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]

    per_tool: dict[str, list[dict]] = {}
    raw_count = 0
    missing_tools: list[str] = []

    for tool in tools:
        combined: list[dict] = []
        any_found = False
        for kind in kinds:
            rpt = _latest_report(tool, kind)
            if rpt:
                any_found = True
                combined.extend(rpt.get("findings", []))
        if any_found:
            per_tool[tool] = combined
            raw_count += len(combined)
        else:
            missing_tools.append(tool)

    if missing_tools:
        print(f"  ! no reports yet from: {', '.join(missing_tools)}", flush=True)
    if not per_tool:
        print("[FAIL] no reports to triangulate yet - run bootstrap+scans for at least one tool first")
        return 2

    clusters = cluster_findings(per_tool)
    summary = {
        "tools": list(per_tool.keys()),
        "tools_count": len(per_tool),
        "total_raw_findings": raw_count,
        "cluster_count": len(clusters),
        "agreement_3": sum(1 for c in clusters if c["agreement"] >= 3),
        "agreement_2": sum(1 for c in clusters if c["agreement"] == 2),
        "agreement_1": sum(1 for c in clusters if c["agreement"] == 1),
    }

    out_dir = REPORTS_DIR / "_triangulation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "triangulation.json").write_text(
        json.dumps({"summary": summary, "clusters": clusters}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "triangulation.md").write_text(
        build_markdown(clusters, summary),
        encoding="utf-8",
    )

    print(f"[OK] Triangulation written -> {out_dir}")
    print(f"   {summary['agreement_3']} certain | {summary['agreement_2']} likely | {summary['agreement_1']} investigate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
