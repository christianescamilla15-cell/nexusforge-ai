"""Local LLM review node — runs a single Ollama model over the
existing automated findings and emits manual_findings.json + report.md
in the same shape as the cloud LLM nodes (Claude, GPT-5.5).

Why this lives in `verification/`: it's a triangulation node, just like
the cloud-based ones, but it runs entirely on a local Ollama instance.
Three focuses are supported (one model per focus, sequential execution
because a 6 GB VRAM laptop GPU only holds one 8B model at a time):

  - security:   evaluate each finding for real exploitability,
                attack vector, and remediation cost
  - technical:  evaluate code quality / refactor priority / perf
                implications of each finding or surface
  - functional: evaluate user-facing impact, doc gaps, UX risk

Each call to Ollama uses `format: "json"` so the response is parseable
deterministically. If the model returns malformed JSON we fall back to
treating the raw text as the finding's description (with a warning).

Usage:
  python3 _local_llm_runner.py \\
      --tool-id deepseek_local \\
      --run-id 20260501T200618Z \\
      --model deepseek-r1:8b \\
      --focus security \\
      --ollama-url http://localhost:11434
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


# ── focus-specific prompts ──────────────────────────────────────────


_PROMPTS: dict[str, str] = {
    "security": """You are a security reviewer. A scanner flagged the following finding in a NexusForge AI codebase. Evaluate it.

Finding:
  category:    {category}
  severity:    {severity}
  file:        {file}:{line}
  title:       {title}
  description: {description}
  scanner:     {source_scanner}

Your job: decide if this is a REAL exploitable issue, a likely false positive, or a known accepted risk. Respond ONLY with this JSON shape, nothing else:

{{
  "verdict": "real" | "false_positive" | "needs_more_context",
  "exploitability": "high" | "medium" | "low" | "n/a",
  "attack_vector": "<one sentence describing how an attacker could exploit this, or 'n/a'>",
  "fix_summary": "<one sentence describing the fix>",
  "fix_effort": "trivial" | "small" | "medium" | "large",
  "confidence": 0.0 to 1.0,
  "notes": "<optional, 1-2 sentences with reasoning>"
}}""",

    "technical": """You are a senior code reviewer. A scanner flagged the following in a NexusForge AI codebase. Evaluate the technical / code-quality impact.

Finding:
  category:    {category}
  severity:    {severity}
  file:        {file}:{line}
  title:       {title}
  description: {description}
  scanner:     {source_scanner}

Your job: assess whether this finding represents a real code-quality / performance / maintainability concern, regardless of security implications. Respond ONLY with this JSON shape:

{{
  "verdict": "real" | "false_positive" | "needs_more_context",
  "impact_area": "performance" | "maintainability" | "correctness" | "testability" | "scalability" | "other",
  "refactor_priority": "high" | "medium" | "low",
  "refactor_summary": "<one sentence describing the refactor>",
  "refactor_effort": "trivial" | "small" | "medium" | "large",
  "confidence": 0.0 to 1.0,
  "notes": "<optional, 1-2 sentences>"
}}""",

    "functional": """You are a product/QA reviewer. A scanner or smoke test flagged the following in a NexusForge AI codebase. Evaluate the user-facing impact.

Finding:
  category:    {category}
  severity:    {severity}
  surface:     {file}
  title:       {title}
  description: {description}
  scanner:     {source_scanner}

Your job: assess whether this finding affects a real user flow, documentation, or UX. Respond ONLY with this JSON shape:

{{
  "verdict": "user_visible" | "internal_only" | "needs_more_context",
  "affected_user_flow": "<which user-facing flow this breaks, or 'none'>",
  "doc_gap": true | false,
  "ux_risk": "high" | "medium" | "low" | "n/a",
  "fix_summary": "<one sentence describing the fix>",
  "confidence": 0.0 to 1.0,
  "notes": "<optional, 1-2 sentences>"
}}""",
}


# ── ollama call ──────────────────────────────────────────────────────


@dataclass
class OllamaConfig:
    base_url: str
    model: str
    timeout_s: float = 120.0
    temperature: float = 0.2  # low for analytical work, not creative


def call_ollama(client: httpx.Client, cfg: OllamaConfig, prompt: str) -> dict:
    """Single non-streaming call. Returns parsed JSON dict.

    Falls back to {"raw_text": "..."} if response can't be parsed
    as JSON — caller should handle gracefully.
    """
    try:
        resp = client.post(
            f"{cfg.base_url}/api/generate",
            json={
                "model": cfg.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": cfg.temperature},
            },
            timeout=cfg.timeout_s,
        )
    except httpx.HTTPError as exc:
        return {"_error": f"ollama HTTP error: {type(exc).__name__}: {exc}"}

    if resp.status_code != 200:
        return {"_error": f"ollama returned {resp.status_code}: {resp.text[:300]}"}

    body = resp.json()
    raw_response = body.get("response", "")
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # Some models wrap the JSON or add prose. Try to extract.
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw_response[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"_error": "model returned non-JSON", "raw_text": raw_response[:500]}


# ── finding selection + processing ──────────────────────────────────


_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def load_findings(run_dir: Path, focus: str) -> list[dict]:
    """Load findings from the harness output, filtered to the relevant
    set for the given focus.

    - security focus uses security_findings.json (≥ medium)
    - technical focus uses security_findings.json (≥ low — wider net for code-quality)
    - functional focus uses functionality_findings.json (any failure)
    """
    out: list[dict] = []
    if focus in ("security", "technical"):
        sec = run_dir / "security_findings.json"
        if sec.exists():
            data = json.loads(sec.read_text(encoding="utf-8"))
            min_rank = _SEVERITY_RANK["medium"] if focus == "security" else _SEVERITY_RANK["low"]
            for f in data.get("findings", []):
                if _SEVERITY_RANK.get(f.get("severity", "info"), 0) >= min_rank:
                    out.append(f)
    if focus in ("functional", "technical"):
        func = run_dir / "functionality_findings.json"
        if func.exists():
            data = json.loads(func.read_text(encoding="utf-8"))
            for f in data.get("findings", []):
                # functionality_findings only contains failures already
                out.append(f)
    return out


def _finding_id(scanner: str, file: str, line: int | None, category: str, title: str) -> str:
    material = f"{scanner}|{file}|{line or 0}|{category}|{title}".encode()
    return hashlib.sha1(material).hexdigest()[:16]


def evaluation_to_finding(
    original: dict,
    evaluation: dict,
    tool_id: str,
    focus: str,
) -> dict:
    """Convert a model evaluation into the unified finding shape so it
    flows into the triangulator alongside the cloud LLM nodes' output."""
    if "_error" in evaluation:
        # Surface the error as a low-severity finding so we don't lose it.
        return {
            "id": _finding_id(tool_id, original.get("file", ""), original.get("line"),
                              "local_llm_error", evaluation["_error"][:80]),
            "source_scanner": tool_id,
            "category": "local_llm_error",
            "severity": "info",
            "file": original.get("file"),
            "line": original.get("line"),
            "title": f"Local LLM evaluation failed for: {original.get('title', '?')[:80]}",
            "description": evaluation["_error"],
            "cwe": None,
            "cvss": None,
        }

    # Confidence < 0.4 → drop verdict to "needs_more_context"
    confidence = evaluation.get("confidence", 0.5)
    if isinstance(confidence, (int, float)) and confidence < 0.4:
        evaluation["verdict"] = "needs_more_context"

    # Build description from the most useful keys per focus.
    description_parts = []
    for key in ("verdict", "exploitability", "attack_vector", "fix_summary",
                "impact_area", "refactor_priority", "refactor_summary",
                "affected_user_flow", "ux_risk", "doc_gap", "notes"):
        val = evaluation.get(key)
        if val is not None and val != "":
            description_parts.append(f"{key}: {val}")

    severity = original.get("severity", "info")
    # If the model says it's a false positive, drop one severity tier
    # so the triangulator deprioritizes it.
    if evaluation.get("verdict") == "false_positive":
        severity = "info"

    return {
        "id": _finding_id(tool_id, original.get("file", ""), original.get("line"),
                          original.get("category", "other"),
                          original.get("title", "?")),
        "source_scanner": tool_id,
        "category": original.get("category", "other"),
        "severity": severity,
        "file": original.get("file"),
        "line": original.get("line"),
        "title": f"[{focus}] {original.get('title', '?')}",
        "description": " | ".join(description_parts) or "no evaluation produced",
        "cwe": original.get("cwe"),
        "cvss": original.get("cvss"),
    }


# ── markdown report ──────────────────────────────────────────────────


def build_markdown(
    tool_id: str,
    run_id: str,
    model: str,
    focus: str,
    raw_evaluations: list[tuple[dict, dict]],
    duration_s: float,
) -> str:
    lines = [
        f"# Local LLM review — `{tool_id}`",
        "",
        f"_Model: `{model}` | Focus: `{focus}` | Run: `{run_id}`_",
        f"_Duration: {duration_s:.1f}s for {len(raw_evaluations)} findings_",
        "",
        "## Summary",
        "",
    ]

    by_verdict: dict[str, int] = {}
    for _, ev in raw_evaluations:
        v = ev.get("verdict") or ("ERROR" if "_error" in ev else "unknown")
        by_verdict[v] = by_verdict.get(v, 0) + 1
    for verdict, count in sorted(by_verdict.items(), key=lambda x: -x[1]):
        lines.append(f"- **{verdict}**: {count}")
    lines.append("")
    lines.append("## Per-finding evaluations")
    lines.append("")

    for original, ev in raw_evaluations:
        title = original.get("title", "?")
        file = original.get("file", "-")
        line = f":{original['line']}" if original.get("line") else ""
        sev = original.get("severity", "?").upper()
        lines.append(f"### [{sev}] {title}")
        lines.append(f"`{file}{line}` (scanner: {original.get('source_scanner', '?')})")
        lines.append("")
        if "_error" in ev:
            lines.append(f"⚠️ **evaluation failed**: {ev['_error']}")
        else:
            for k, v in ev.items():
                if k.startswith("_"):
                    continue
                lines.append(f"- **{k}**: {v}")
        lines.append("")

    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tool-id", required=True, help="e.g. deepseek_local")
    p.add_argument("--run-id", required=True)
    p.add_argument("--model", required=True, help="ollama model tag, e.g. deepseek-r1:8b")
    p.add_argument("--focus", required=True, choices=list(_PROMPTS.keys()))
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--max-findings", type=int, default=50,
                   help="Cap on findings to evaluate (avoid runaway on noisy scans)")
    p.add_argument("--repo-root",
                   default=str(Path(__file__).resolve().parent.parent))
    args = p.parse_args()

    repo_root = Path(args.repo_root)
    run_dir = repo_root / "verification" / "reports" / args.tool_id / args.run_id
    if not run_dir.is_dir():
        # No bootstrap run for this tool yet — create the dir + minimal
        # metadata so the runner can still emit something.
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run_metadata.json").write_text(
            json.dumps({"tool_id": args.tool_id, "run_id": args.run_id,
                        "note": "created by _local_llm_runner without bootstrap"}, indent=2),
            encoding="utf-8",
        )

    findings = load_findings(run_dir, args.focus)

    # Often the local node is run AFTER another tool's bootstrap; if
    # this tool's own findings dirs are empty, fall back to the most
    # recent run from any tool that DID run the harness (claude_security,
    # gpt55, etc.). This makes the local node useful even without its
    # own bootstrap pass.
    if not findings:
        reports_root = repo_root / "verification" / "reports"
        for sibling_tool in sorted(reports_root.iterdir()):
            if not sibling_tool.is_dir() or sibling_tool.name.startswith(("_", ".")) or sibling_tool.name == args.tool_id:
                continue
            for sibling_run in sorted(sibling_tool.iterdir(), reverse=True):
                if not sibling_run.is_dir():
                    continue
                fallback = load_findings(sibling_run, args.focus)
                if fallback:
                    print(f"  (using findings from {sibling_tool.name}/{sibling_run.name} as input)")
                    findings = fallback
                    break
            if findings:
                break

    if not findings:
        print(f"  ! no findings to evaluate for focus={args.focus}")
        out = {"tool_id": args.tool_id, "run_id": args.run_id, "scan_kind": args.focus,
               "model": args.model, "finding_count": 0, "findings": []}
        (run_dir / f"manual_findings_{args.focus}.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8")
        return 0

    findings = findings[:args.max_findings]
    print(f"  Evaluating {len(findings)} findings with {args.model} (focus={args.focus})…")

    cfg = OllamaConfig(base_url=args.ollama_url, model=args.model)
    raw_evaluations: list[tuple[dict, dict]] = []
    started = time.time()

    with httpx.Client() as client:
        for i, finding in enumerate(findings, start=1):
            prompt = _PROMPTS[args.focus].format(
                category=finding.get("category", "?"),
                severity=finding.get("severity", "?"),
                file=finding.get("file", "?"),
                line=finding.get("line", ""),
                title=finding.get("title", "?"),
                description=(finding.get("description", "") or "")[:1000],
                source_scanner=finding.get("source_scanner", "?"),
            )
            t0 = time.time()
            ev = call_ollama(client, cfg, prompt)
            elapsed = time.time() - t0
            verdict = ev.get("verdict") or ("ERR" if "_error" in ev else "?")
            print(f"    [{i}/{len(findings)}] {finding.get('title', '?')[:60]}  → {verdict} ({elapsed:.1f}s)")
            raw_evaluations.append((finding, ev))

    duration = time.time() - started

    # Write manual_findings.json (unified shape)
    findings_out = [
        evaluation_to_finding(orig, ev, args.tool_id, args.focus)
        for orig, ev in raw_evaluations
    ]
    json_path = run_dir / f"manual_findings_{args.focus}.json"
    json_path.write_text(
        json.dumps({
            "tool_id": args.tool_id,
            "run_id": args.run_id,
            "scan_kind": args.focus,
            "model": args.model,
            "duration_s": duration,
            "finding_count": len(findings_out),
            "findings": findings_out,
        }, indent=2),
        encoding="utf-8",
    )

    # Write per-focus markdown report so an analyst can skim
    md_path = run_dir / f"local_review_{args.focus}.md"
    md_path.write_text(
        build_markdown(args.tool_id, args.run_id, args.model, args.focus,
                       raw_evaluations, duration),
        encoding="utf-8",
    )

    print(f"  ✓ {args.tool_id}/{args.focus}: {len(findings_out)} evaluations in {duration:.1f}s")
    print(f"    JSON: {json_path}")
    print(f"    MD:   {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
