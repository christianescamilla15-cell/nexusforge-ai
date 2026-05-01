"""Normalize raw scanner outputs into a unified findings.json.

Each scanner has its own output schema. We collapse all of them into
the shape declared in `verification/templates/finding.schema.json`:

    {
      "tool_id": "claude_security",
      "run_id": "20260501T140000Z",
      "scan_kind": "security",
      "findings": [
        {
          "id": "<deterministic hash>",
          "source_scanner": "mythos|pip_audit|npm_audit|gitleaks|semgrep|schemathesis",
          "category": "secrets|auth|injection|crypto|config|deps|fuzz|other",
          "severity": "critical|high|medium|low|info",
          "file": "backend/app/auth/foo.py",
          "line": 42,
          "title": "Hardcoded JWT secret",
          "description": "Found a literal that matches a JWT signing key pattern...",
          "cwe": "CWE-798",
          "cvss": null
        },
        ...
      ]
    }

Determinism: each finding's `id` is sha1(source_scanner + file + line +
category + title)[:16]. Stable across runs so triangulation can match.
Don't include any timestamp / counter in the hash material — that would
break cross-tool agreement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


SEVERITY_NORMALIZE = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
    "info": "info",
    "warning": "medium",
    "error": "high",
}


def _finding_id(scanner: str, file: str, line: int | None, category: str, title: str) -> str:
    material = f"{scanner}|{file}|{line or 0}|{category}|{title}".encode()
    return hashlib.sha1(material).hexdigest()[:16]


def _norm_severity(raw: str | None) -> str:
    if not raw:
        return "info"
    return SEVERITY_NORMALIZE.get(raw.lower(), "info")


def normalize_mythos(raw: dict) -> list[dict]:
    out = []
    for cat in raw.get("categories", []):
        cat_name = cat.get("name", "other")
        for f in cat.get("findings", []):
            file = f.get("file") or f.get("path") or "unknown"
            line = f.get("line")
            title = f.get("title") or f.get("rule") or "Mythos finding"
            severity = _norm_severity(f.get("severity"))
            out.append({
                "id": _finding_id("mythos", file, line, cat_name, title),
                "source_scanner": "mythos",
                "category": cat_name,
                "severity": severity,
                "file": file,
                "line": line,
                "title": title,
                "description": f.get("description") or f.get("detail") or "",
                "cwe": f.get("cwe"),
                "cvss": None,
            })
    return out


def normalize_pip_audit(raw) -> list[dict]:
    out = []
    # pip-audit JSON shape: {"dependencies": [{"name": ..., "vulns": [...]}, ...]}
    deps = raw.get("dependencies", []) if isinstance(raw, dict) else raw
    for dep in deps:
        name = dep.get("name", "?")
        for vuln in dep.get("vulns", []):
            vid = vuln.get("id", "UNKNOWN")
            title = f"{name} — {vid}"
            out.append({
                "id": _finding_id("pip_audit", f"backend/requirements.txt", None, "deps", title),
                "source_scanner": "pip_audit",
                "category": "deps",
                "severity": _norm_severity(vuln.get("severity") or "high"),
                "file": "backend/requirements.txt",
                "line": None,
                "title": title,
                "description": vuln.get("description") or "",
                "cwe": None,
                "cvss": None,
            })
    return out


def normalize_npm_audit(raw: dict) -> list[dict]:
    out = []
    vulns = raw.get("vulnerabilities", {}) if isinstance(raw, dict) else {}
    for name, vdata in vulns.items():
        if not isinstance(vdata, dict):
            continue
        title = f"{name} — {vdata.get('severity', '?')}"
        out.append({
            "id": _finding_id("npm_audit", "frontend/package.json", None, "deps", title),
            "source_scanner": "npm_audit",
            "category": "deps",
            "severity": _norm_severity(vdata.get("severity")),
            "file": "frontend/package.json",
            "line": None,
            "title": title,
            "description": str(vdata.get("via", ""))[:500],
            "cwe": None,
            "cvss": None,
        })
    return out


def normalize_gitleaks(raw) -> list[dict]:
    out = []
    items = raw if isinstance(raw, list) else raw.get("findings", []) if isinstance(raw, dict) else []
    for f in items:
        file = f.get("File", "unknown")
        line = f.get("StartLine")
        rule = f.get("RuleID", "secret")
        title = f"Possible secret: {rule}"
        out.append({
            "id": _finding_id("gitleaks", file, line, "secrets", title),
            "source_scanner": "gitleaks",
            "category": "secrets",
            "severity": "high",
            "file": file,
            "line": line,
            "title": title,
            "description": (f.get("Description") or "")[:500],
            "cwe": "CWE-798",
            "cvss": None,
        })
    return out


def normalize_semgrep(raw: dict) -> list[dict]:
    out = []
    for r in raw.get("results", []):
        path = r.get("path", "unknown")
        line = r.get("start", {}).get("line") or None
        check = r.get("check_id", "semgrep")
        title = check.split(".")[-1] if isinstance(check, str) else "semgrep"
        sev = (r.get("extra", {}).get("severity") or "INFO").lower()
        # semgrep p/security-audit emits ERROR / WARNING / INFO
        sev_map = {"error": "high", "warning": "medium", "info": "low"}
        out.append({
            "id": _finding_id("semgrep", path, line, "sast", title),
            "source_scanner": "semgrep",
            "category": "sast",
            "severity": sev_map.get(sev, "low"),
            "file": path,
            "line": line,
            "title": title,
            "description": (r.get("extra", {}).get("message") or "")[:500],
            "cwe": (r.get("extra", {}).get("metadata", {}) or {}).get("cwe"),
            "cvss": None,
        })
    return out


def normalize_schemathesis(raw) -> list[dict]:
    out = []
    items = raw if isinstance(raw, list) else raw.get("checks", []) if isinstance(raw, dict) else []
    for f in items:
        if isinstance(f, dict) and not f.get("passed", True):
            endpoint = f.get("path") or f.get("endpoint") or "unknown"
            title = f"API contract: {f.get('name', 'check')}"
            out.append({
                "id": _finding_id("schemathesis", endpoint, None, "fuzz", title),
                "source_scanner": "schemathesis",
                "category": "fuzz",
                "severity": "medium",
                "file": endpoint,
                "line": None,
                "title": title,
                "description": (str(f.get("message", "")))[:500],
                "cwe": None,
                "cvss": None,
            })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", required=True)
    p.add_argument("--tool-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    raw_dir = Path(args.raw_dir)
    findings: list[dict] = []

    for name, normalizer in [
        ("mythos.json", normalize_mythos),
        ("pip_audit.json", normalize_pip_audit),
        ("npm_audit.json", normalize_npm_audit),
        ("gitleaks.json", normalize_gitleaks),
        ("semgrep.json", normalize_semgrep),
        ("schemathesis.json", normalize_schemathesis),
    ]:
        path = raw_dir / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  warning: {name} not parseable, skipping", file=sys.stderr)
            continue
        findings.extend(normalizer(data))

    output = {
        "tool_id": args.tool_id,
        "run_id": args.run_id,
        "scan_kind": "security",
        "finding_count": len(findings),
        "findings": findings,
    }
    Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
