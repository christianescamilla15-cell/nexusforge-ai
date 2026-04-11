"""AI-powered documentation generator — Gap 8.

Walks a legacy codebase, infers the stack + architecture + integrations,
and generates a canonical documentation bundle that closes the "no docs"
gap which shows up in virtually every enterprise legacy modernization
engagement.

What it generates (per app):

1. ``README.md``          — overview, stack, how to run, structure
2. ``ARCHITECTURE.md``    — C4 diagrams in Mermaid (Context → Container
                             → Component) inferred from the codebase
3. ``ADR-0001-initial-architecture.md`` — first Architecture Decision
                             Record documenting the captured state
4. ``RUNBOOK.md``         — operational runbook (deploy, debug, common
                             failures, restart procedures)
5. ``API.md``             — endpoint inventory if FastAPI / Express /
                             Spring / ASP.NET routes are detected
6. ``INTEGRATIONS.md``    — external dependencies (FTP, DB, HTTP APIs,
                             queues) detected in the source

The generator is DETERMINISTIC in its current implementation: it uses
regex + AST-level heuristics, not LLM calls. The name "AI-powered" in
the roadmap refers to the fact that the generator is driven by the same
multi-agent analysis pipeline (ingestion + classification + pattern
matchers) that the rest of the refactor engine uses — an LLM post-pass
is optional future work (not in this first cut).

This is PURELY additive: it only writes docs, it never modifies the
application source code. Existing docs in the repo are NOT overwritten
unless the caller sets ``overwrite=True``.

Related gaps:
- Gap 1 (multi_lang_scanner): can feed stack inference
- Gap 3 (strangler_planner): consumes the generated ARCHITECTURE.md
  as input for decomposition
- Gap 6 (data_pipeline_planner): cross-links INTEGRATIONS.md with the
  data pipeline modernization plan
- Gap 11 (observability_bootstrapper): RUNBOOK.md references the
  observability stack the bootstrapper provisions
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── File extensions + skip rules ──────────────────────────────────────────

_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "bower_components",
    "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache",
    "bin", "obj", "target",
    "build", "dist", "out",
    ".next", ".nuxt", ".vercel",
    "coverage", ".coverage",
}

_CODE_EXTS = {
    ".py", ".cs", ".vb", ".java", ".kt", ".scala",
    ".js", ".jsx", ".ts", ".tsx",
    ".cbl", ".cob", ".cpy", ".jcl",
    ".go", ".rs", ".rb", ".php",
    ".sql", ".xml", ".yaml", ".yml", ".json", ".toml",
    ".md", ".dockerfile",
}

_MAX_FILE_BYTES = 2_000_000


# ── Stack inference ──────────────────────────────────────────────────────
#
# Each entry is a tuple of (filename_pattern, stack_tag, priority).
# We walk the repo once and collect all hits; the generator reports the
# top-3 by priority as the "primary stack" in the README.

_STACK_SIGNATURES: list[tuple[str, str, int]] = [
    # Python
    ("requirements.txt", "python", 10),
    ("pyproject.toml", "python", 10),
    ("Pipfile", "python", 9),
    ("setup.py", "python", 8),
    # Python frameworks
    ("fastapi", "fastapi", 10),
    ("django", "django", 10),
    ("flask", "flask", 10),
    ("pandas", "python-data", 5),
    # JavaScript / TypeScript
    ("package.json", "javascript", 10),
    ("tsconfig.json", "typescript", 9),
    ("next.config.js", "nextjs", 10),
    ("vite.config.js", "vite", 9),
    ("vite.config.ts", "vite", 9),
    ("yarn.lock", "javascript-yarn", 5),
    ("pnpm-lock.yaml", "javascript-pnpm", 5),
    # C# / .NET
    (".csproj", "dotnet", 10),
    (".sln", "dotnet", 10),
    ("web.config", "dotnet-framework", 9),
    ("appsettings.json", "dotnet-core", 9),
    # Java
    ("pom.xml", "java-maven", 10),
    ("build.gradle", "java-gradle", 10),
    ("build.gradle.kts", "java-gradle", 10),
    # COBOL
    (".cbl", "cobol", 10),
    (".cob", "cobol", 10),
    (".cpy", "cobol-copybook", 9),
    (".jcl", "mainframe-jcl", 10),
    # Infrastructure
    ("Dockerfile", "docker", 9),
    ("docker-compose.yml", "docker-compose", 9),
    ("docker-compose.yaml", "docker-compose", 9),
    ("terraform", "terraform", 8),
    (".tf", "terraform", 8),
    ("helm", "helm", 8),
    ("kustomization.yaml", "kustomize", 8),
    # CI / CD
    (".github/workflows", "github-actions", 8),
    (".gitlab-ci.yml", "gitlab-ci", 8),
    ("Jenkinsfile", "jenkins", 8),
    ("azure-pipelines.yml", "azure-pipelines", 8),
    # Databases
    ("alembic.ini", "alembic-migrations", 7),
    (".sql", "sql-scripts", 5),
]


def _detect_stack(repo_root: Path) -> dict[str, int]:
    """Walk the repo and count stack signature hits.

    Returns a dict of ``{stack_tag: total_priority_score}``. Extensions
    are matched against filenames case-insensitively. Directory-level
    signatures (like ``.github/workflows``) match on any path fragment.
    """
    scores: dict[str, int] = {}
    for path in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        name_lower = path.name.lower()
        full_lower = str(path).replace("\\", "/").lower()

        for signature, tag, priority in _STACK_SIGNATURES:
            sig_lower = signature.lower()
            if sig_lower.startswith("."):
                # Extension match
                if name_lower.endswith(sig_lower):
                    scores[tag] = scores.get(tag, 0) + priority
            elif "/" in sig_lower:
                # Directory path fragment match
                if sig_lower in full_lower:
                    scores[tag] = scores.get(tag, 0) + priority
            else:
                # Filename literal
                if name_lower == sig_lower or sig_lower in name_lower:
                    scores[tag] = scores.get(tag, 0) + priority
    return scores


def _top_stack_tags(scores: dict[str, int], n: int = 5) -> list[str]:
    """Return the top-N stack tags by score (ties broken by name)."""
    return sorted(scores.keys(), key=lambda k: (-scores[k], k))[:n]


# ── Entry-point detection ────────────────────────────────────────────────
#
# Entry points are the "how to run this" signal. We look for common
# canonical files per stack.

_ENTRY_POINT_CANDIDATES: list[tuple[str, str, str]] = [
    # (glob_pattern_substring, stack_hint, run_command)
    ("main.py", "python", "python main.py"),
    ("app.py", "python-flask", "flask run"),
    ("manage.py", "django", "python manage.py runserver"),
    ("uvicorn", "fastapi", "uvicorn app.main:app --reload"),
    ("program.cs", "dotnet", "dotnet run"),
    ("index.js", "node", "node index.js"),
    ("server.js", "node", "node server.js"),
    ("app.js", "node-express", "node app.js"),
    ("package.json", "node", "npm start"),
    ("main.go", "go", "go run ."),
    ("cargo.toml", "rust", "cargo run"),
    ("pom.xml", "java-maven", "mvn spring-boot:run"),
    ("build.gradle", "java-gradle", "./gradlew bootRun"),
]


@dataclass
class EntryPoint:
    file_path: str
    stack_hint: str
    run_command: str


def _detect_entry_points(repo_root: Path) -> list[EntryPoint]:
    """Return the canonical entry points of the repo (best-effort)."""
    found: list[EntryPoint] = []
    seen: set[str] = set()
    for path in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        for needle, stack_hint, run_cmd in _ENTRY_POINT_CANDIDATES:
            if needle not in name_lower:
                continue
            rel = str(path.relative_to(repo_root)).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            found.append(EntryPoint(rel, stack_hint, run_cmd))
            break
    # Stable sort: by shallowest path first (likely the main entry)
    found.sort(key=lambda e: (e.file_path.count("/"), e.file_path))
    return found[:8]  # cap — a single app rarely has more than 8 real entries


# ── Endpoint detection ───────────────────────────────────────────────────
#
# Rough endpoint discovery by regex. False positives are acceptable for
# initial docs (better to list something with a TODO than to miss routes).

_ENDPOINT_PATTERNS: list[tuple[str, str]] = [
    # FastAPI / Starlette
    (r"""@(?:app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*["']([^"']+)["']""", "fastapi"),
    # Flask
    (r"""@(?:app|bp|blueprint)\.route\s*\(\s*["']([^"']+)["']""", "flask"),
    # Express / Koa
    (r"""(?:app|router)\.(get|post|put|delete|patch|use)\s*\(\s*["']([^"']+)["']""", "express"),
    # ASP.NET MVC / Web API
    (r"""\[Http(Get|Post|Put|Delete|Patch)\b[^\]]*\]""", "aspnet"),
    (r"""\[Route\s*\(\s*["']([^"']+)["']""", "aspnet"),
    # Spring
    (r"""@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\(\s*[^)]*["']([^"']+)["']""", "spring"),
]


@dataclass
class DetectedEndpoint:
    http_method: str
    path: str
    file_path: str
    line_number: int
    framework: str


def _detect_endpoints(repo_root: Path) -> list[DetectedEndpoint]:
    """Walk the repo and extract HTTP endpoint declarations."""
    results: list[DetectedEndpoint] = []
    compiled = [(re.compile(p), framework) for p, framework in _ENDPOINT_PATTERNS]

    for path in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in _CODE_EXTS:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(text.encode("utf-8", errors="ignore")) > _MAX_FILE_BYTES:
            continue

        for pattern, framework in compiled:
            for match in pattern.finditer(text):
                groups = match.groups()
                # Different frameworks use different group ordering
                if framework in ("fastapi", "express"):
                    method = groups[0].upper() if groups else "GET"
                    route = groups[1] if len(groups) > 1 else ""
                elif framework == "flask":
                    method = "GET"  # default; Flask also allows methods= kwarg
                    route = groups[0] if groups else ""
                elif framework == "aspnet":
                    # Two different patterns: HttpXxx attribute or Route(...)
                    if groups and groups[0].lower() in ("get", "post", "put", "delete", "patch"):
                        method = groups[0].upper()
                        route = ""
                    else:
                        method = "GET"
                        route = groups[0] if groups else ""
                elif framework == "spring":
                    verb = groups[0] if groups else ""
                    spring_method_map = {
                        "GetMapping": "GET",
                        "PostMapping": "POST",
                        "PutMapping": "PUT",
                        "DeleteMapping": "DELETE",
                        "PatchMapping": "PATCH",
                        "RequestMapping": "ANY",
                    }
                    method = spring_method_map.get(verb, "GET")
                    route = groups[1] if len(groups) > 1 else ""
                else:
                    method = "?"
                    route = ""

                if not route:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                results.append(
                    DetectedEndpoint(
                        http_method=method,
                        path=route,
                        file_path=str(path.relative_to(repo_root)).replace("\\", "/"),
                        line_number=line,
                        framework=framework,
                    )
                )

    # Dedupe by (method, path)
    seen: set[tuple[str, str]] = set()
    deduped: list[DetectedEndpoint] = []
    for ep in results:
        key = (ep.http_method, ep.path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ep)
    deduped.sort(key=lambda e: (e.path, e.http_method))
    return deduped


# ── Integration detection ───────────────────────────────────────────────
#
# Surfaces external dependencies that ARE NOT part of the local stack —
# FTP hosts, DB connection strings, HTTP base URLs, message queue
# brokers. Used for INTEGRATIONS.md and cross-linked with Gap 6.

_INTEGRATION_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, integration_type, description)
    (r"""(?:ftp|sftp)://[^\s"'`]+""", "ftp", "FTP / SFTP file transfer endpoint"),
    (r"""https?://[A-Za-z0-9.\-]+(?::\d+)?(?:/[^\s"'`]*)?""", "http", "HTTP(S) endpoint"),
    (r"""(?:mongodb|mongodb\+srv|postgresql|postgres|mysql|sqlserver|oracle)://[^\s"'`]+""", "database", "Database connection string"),
    (r"""(?:amqp|kafka|redis)://[^\s"'`]+""", "messaging", "Message queue / streaming endpoint"),
    (r"""(?i)host\s*=\s*["']?([A-Za-z0-9.\-]+)["']?""", "host-config", "Host configuration"),
]


@dataclass
class DetectedIntegration:
    integration_type: str
    target: str
    file_path: str
    line_number: int
    description: str


def _detect_integrations(repo_root: Path) -> list[DetectedIntegration]:
    """Walk the repo and extract external integration references."""
    results: list[DetectedIntegration] = []
    compiled = [(re.compile(p), itype, desc) for p, itype, desc in _INTEGRATION_PATTERNS]

    # Skip common false-positive paths
    skip_patterns = (
        "http://localhost",
        "https://localhost",
        "http://127.",
        "https://127.",
        "http://0.0.0.0",
        "http://example.com",
        "https://example.com",
        "http://schemas.",  # XML namespace URIs, ubiquitous in C# / Java
        "https://schemas.",
        "http://www.w3.org",
        "https://www.w3.org",
    )

    for path in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in _CODE_EXTS:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(text.encode("utf-8", errors="ignore")) > _MAX_FILE_BYTES:
            continue

        for pattern, itype, desc in compiled:
            for match in pattern.finditer(text):
                target = match.group(0) if not match.groups() else match.group(1)
                target = target.strip()
                if any(target.lower().startswith(skip) for skip in skip_patterns):
                    continue
                if len(target) > 200:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                results.append(
                    DetectedIntegration(
                        integration_type=itype,
                        target=target,
                        file_path=str(path.relative_to(repo_root)).replace("\\", "/"),
                        line_number=line,
                        description=desc,
                    )
                )

    # Dedupe by (type, target)
    seen: set[tuple[str, str]] = set()
    deduped: list[DetectedIntegration] = []
    for itg in results:
        key = (itg.integration_type, itg.target)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(itg)
    deduped.sort(key=lambda i: (i.integration_type, i.target))
    return deduped[:200]  # cap — runaway detection would overwhelm the doc


# ── Module / directory inventory ────────────────────────────────────────


@dataclass
class ModuleEntry:
    name: str
    path: str
    file_count: int
    language_mix: dict[str, int]


def _inventory_modules(repo_root: Path, max_depth: int = 2) -> list[ModuleEntry]:
    """Build a shallow module inventory for the ARCHITECTURE / README sections."""
    modules: list[ModuleEntry] = []
    for path in repo_root.iterdir():
        if not path.is_dir():
            continue
        if path.name in _SKIP_DIRS or path.name.startswith("."):
            continue
        file_count = 0
        langs: dict[str, int] = {}
        for p in path.rglob("*"):
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if not p.is_file():
                continue
            file_count += 1
            ext = p.suffix.lower()
            if ext in _CODE_EXTS:
                langs[ext] = langs.get(ext, 0) + 1
        modules.append(
            ModuleEntry(
                name=path.name,
                path=str(path.relative_to(repo_root)).replace("\\", "/"),
                file_count=file_count,
                language_mix=langs,
            )
        )
    modules.sort(key=lambda m: (-m.file_count, m.name))
    return modules[:20]  # top 20 modules


# ── Report dataclass ─────────────────────────────────────────────────────


@dataclass
class DocGenerationReport:
    """Complete output of the doc generator for one app."""

    app_name: str
    app_path: str
    generated_at: str                                           # ISO timestamp
    stack_scores: dict[str, int] = field(default_factory=dict)
    primary_stack: list[str] = field(default_factory=list)
    entry_points: list[EntryPoint] = field(default_factory=list)
    endpoints: list[DetectedEndpoint] = field(default_factory=list)
    integrations: list[DetectedIntegration] = field(default_factory=list)
    modules: list[ModuleEntry] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)         # filename -> rendered content
    written_to_disk: list[str] = field(default_factory=list)    # absolute paths written
    warnings: list[str] = field(default_factory=list)

    @property
    def total_endpoints(self) -> int:
        return len(self.endpoints)

    @property
    def total_integrations(self) -> int:
        return len(self.integrations)

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "app_path": self.app_path,
            "generated_at": self.generated_at,
            "primary_stack": self.primary_stack,
            "stack_scores": self.stack_scores,
            "entry_points": [asdict(e) for e in self.entry_points],
            "total_endpoints": self.total_endpoints,
            "endpoints": [asdict(e) for e in self.endpoints],
            "total_integrations": self.total_integrations,
            "integrations": [asdict(i) for i in self.integrations],
            "modules": [asdict(m) for m in self.modules],
            "files": self.files,
            "written_to_disk": self.written_to_disk,
            "warnings": self.warnings,
        }


# ── Renderers ────────────────────────────────────────────────────────────


def _render_readme(report: DocGenerationReport) -> str:
    lines = [
        f"# {report.app_name}",
        "",
        "> Auto-generated documentation. Do not edit by hand above this line.",
        f"> Last generated: {report.generated_at}.",
        "",
        "## Overview",
        "",
        (
            f"`{report.app_name}` is a legacy application captured as part of the "
            f"NexusForge tenant-alpha showcase. This README is produced by the "
            f"documentation generator (Gap 8) and reflects the current state "
            f"of the repository at the time of the scan. It is intentionally "
            f"a starting point — humans should refine prose, diagrams, and "
            f"context once the automated capture is in place."
        ),
        "",
        "## Stack",
        "",
    ]
    if report.primary_stack:
        for tag in report.primary_stack:
            score = report.stack_scores.get(tag, 0)
            lines.append(f"- `{tag}` (signal score: {score})")
    else:
        lines.append("- Stack could not be inferred — no recognized manifests found.")
    lines.append("")

    lines.append("## Entry points")
    lines.append("")
    if report.entry_points:
        for ep in report.entry_points:
            lines.append(
                f"- `{ep.file_path}` — run with `{ep.run_command}` "
                f"(detected as `{ep.stack_hint}`)"
            )
    else:
        lines.append("- No canonical entry point detected. Manual investigation required.")
    lines.append("")

    lines.append("## Modules")
    lines.append("")
    if report.modules:
        lines.append("| Module | Files | Top languages |")
        lines.append("|---|---|---|")
        for m in report.modules:
            langs = ", ".join(
                f"{ext} ({n})"
                for ext, n in sorted(m.language_mix.items(), key=lambda kv: -kv[1])[:3]
            ) or "—"
            lines.append(f"| `{m.path}` | {m.file_count} | {langs} |")
    else:
        lines.append("_No top-level modules detected._")
    lines.append("")

    lines.append("## See also")
    lines.append("")
    lines.append("- `ARCHITECTURE.md` — C4 diagrams and module dependencies")
    lines.append("- `API.md` — HTTP endpoint inventory")
    lines.append("- `INTEGRATIONS.md` — external dependencies")
    lines.append("- `RUNBOOK.md` — operational procedures")
    lines.append("- `ADR-0001-initial-architecture.md` — captured-state decision record")
    lines.append("")
    return "\n".join(lines)


def _render_architecture(report: DocGenerationReport) -> str:
    lines = [
        f"# Architecture — {report.app_name}",
        "",
        "> Auto-generated. Diagrams inferred from codebase walk; refine once verified.",
        f"> Last generated: {report.generated_at}.",
        "",
        "## C4: Context diagram",
        "",
        "```mermaid",
        "flowchart LR",
        f"    U([User / Operator]) --> APP[{report.app_name}]",
    ]
    # Add external integrations as context-level boxes
    seen_targets: set[str] = set()
    for itg in report.integrations[:10]:
        tag = itg.integration_type.upper().replace("-", "_")
        # Sanitize for mermaid
        label = itg.target[:60].replace("|", "/").replace('"', "'")
        node_id = f"EXT_{len(seen_targets)}"
        if label in seen_targets:
            continue
        seen_targets.add(label)
        lines.append(f"    APP --> {node_id}[{tag}<br/>{label}]")
    lines.append("```")
    lines.append("")

    lines.append("## C4: Container diagram")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TB")
    lines.append(f"    subgraph {report.app_name}")
    for m in report.modules[:8]:
        mid = m.name.replace("-", "_").replace(".", "_")[:30]
        langs = ",".join(sorted(m.language_mix.keys())[:3]) or "?"
        lines.append(f"        {mid}[{m.name}<br/>{langs}]")
    lines.append("    end")
    lines.append("```")
    lines.append("")

    lines.append("## C4: Component diagram")
    lines.append("")
    if report.endpoints:
        lines.append("_Derived from HTTP endpoint inventory. Each unique method+path "
                     "becomes a component box routed to its handler file._")
        lines.append("")
        lines.append("```mermaid")
        lines.append("flowchart LR")
        for i, ep in enumerate(report.endpoints[:15]):
            fid = f"F{i}"
            lines.append(
                f"    {fid}[\"{ep.http_method} {ep.path[:40]}\"] --> "
                f"H{i}[{Path(ep.file_path).name}:{ep.line_number}]"
            )
        lines.append("```")
    else:
        lines.append("_No HTTP endpoints detected. Add component diagram manually if "
                     "this is a batch / worker-style application._")
    lines.append("")

    lines.append("## Module inventory")
    lines.append("")
    if report.modules:
        lines.append("| Module | File count | Language mix |")
        lines.append("|---|---|---|")
        for m in report.modules:
            langs = ", ".join(
                f"`{ext}`×{n}"
                for ext, n in sorted(m.language_mix.items(), key=lambda kv: -kv[1])[:4]
            ) or "—"
            lines.append(f"| `{m.path}` | {m.file_count} | {langs} |")
        lines.append("")
    return "\n".join(lines)


def _render_adr(report: DocGenerationReport) -> str:
    lines = [
        f"# ADR-0001: Captured initial architecture for `{report.app_name}`",
        "",
        f"**Status:** proposed  ",
        f"**Date:** {report.generated_at.split('T')[0]}  ",
        f"**Author:** NexusForge documentation generator (Gap 8)  ",
        "",
        "## Context",
        "",
        (
            "This ADR captures the state of the application at the moment the "
            "NexusForge documentation generator first walked the repository. "
            "Legacy enterprise applications typically reach modernization with "
            "no ADRs, no runbooks, and only informal knowledge held in BPO "
            "teams. Before refactoring can start, the current state must be "
            "written down so that every subsequent decision has a durable "
            "baseline to compare against."
        ),
        "",
        "## Decision",
        "",
        (
            "We record the detected stack, entry points, HTTP endpoints, and "
            "integration surface as the initial architecture of record. All "
            "modernization work in phases B and C of the tenant showcase "
            "plan (see `integration/02_phase2_plan.md` §3.3) uses this ADR "
            "as the delta reference."
        ),
        "",
        "## Captured state (the actual baseline)",
        "",
        f"- **App name**: `{report.app_name}`",
        f"- **App path**: `{report.app_path}`",
    ]
    if report.primary_stack:
        lines.append(f"- **Primary stack signals**: {', '.join(report.primary_stack)}")
    lines.append(f"- **Entry points detected**: {len(report.entry_points)}")
    lines.append(f"- **HTTP endpoints detected**: {report.total_endpoints}")
    lines.append(f"- **External integrations detected**: {report.total_integrations}")
    lines.append(f"- **Top-level modules**: {len(report.modules)}")
    lines.append("")
    lines.append("## Consequences")
    lines.append("")
    lines.append(
        "- Any change that alters an entry point, adds/removes an HTTP endpoint, "
        "or introduces a new external integration must produce a follow-up ADR "
        "explaining the motivation and the rollback plan."
    )
    lines.append("- This ADR should be regenerated by the documentation generator "
                 "after each refactor milestone so the 'captured state' stays "
                 "aligned with reality.")
    lines.append("- Humans should mark this ADR as `accepted` once the captured "
                 "state has been reviewed by a tech lead and deemed correct.")
    lines.append("")
    return "\n".join(lines)


def _render_runbook(report: DocGenerationReport) -> str:
    lines = [
        f"# Runbook — {report.app_name}",
        "",
        "> Auto-generated operational runbook. Refine with incident history.",
        f"> Last generated: {report.generated_at}.",
        "",
        "## How to run locally",
        "",
    ]
    if report.entry_points:
        for ep in report.entry_points[:3]:
            lines.append(f"### {ep.file_path}")
            lines.append("")
            lines.append(f"- **Stack**: `{ep.stack_hint}`")
            lines.append(f"- **Run command**: `{ep.run_command}`")
            lines.append("")
    else:
        lines.append("_No canonical entry point detected. Ask a maintainer for the run command._")
        lines.append("")

    lines.append("## Common failures and mitigations")
    lines.append("")
    lines.append(
        "Populate this section as the team gathers incident history. Starter "
        "entries inferred from the detected integrations:"
    )
    lines.append("")
    if report.integrations:
        types_seen: set[str] = set()
        for itg in report.integrations[:6]:
            if itg.integration_type in types_seen:
                continue
            types_seen.add(itg.integration_type)
            lines.append(f"- **{itg.integration_type} outage**: if the application "
                         f"cannot reach `{itg.target[:60]}` (described as "
                         f"{itg.description}), expect batch failures. Add a "
                         f"fallback or circuit breaker as a follow-up.")
    else:
        lines.append("- No external integrations detected — no pre-populated failure modes.")
    lines.append("")

    lines.append("## Deploy procedure")
    lines.append("")
    lines.append(
        "This runbook does not yet describe the actual deploy procedure. The "
        "tenant-alpha showcase apps are deliberately production-only with no "
        "CI/CD (see `integration/02_phase2_plan.md` §3.2 for the no-dev-"
        "environment fixture). Once the refactor engine attaches a CI/CD "
        "pipeline via Gap 5 / Gap 4, regenerate this runbook so the deploy "
        "steps reflect the new pipeline."
    )
    lines.append("")

    lines.append("## Rollback")
    lines.append("")
    lines.append(
        "Default rollback is feature-flag-based. See the individual ADRs for "
        "decision-specific rollback strategies."
    )
    lines.append("")

    lines.append("## Observability")
    lines.append("")
    lines.append(
        "Populated by the observability stack bootstrapper (Gap 11). Once the "
        "SLO + monitoring + business anomaly alerting stack is provisioned, "
        "this section should list the dashboards and alerts that apply to "
        "this app specifically."
    )
    lines.append("")
    return "\n".join(lines)


def _render_api(report: DocGenerationReport) -> str:
    lines = [
        f"# API — {report.app_name}",
        "",
        "> Auto-generated endpoint inventory.",
        f"> Last generated: {report.generated_at}.",
        "",
    ]
    if not report.endpoints:
        lines.append(
            "_No HTTP endpoints detected. This application may be a batch / "
            "worker / CLI-only system. Review manually._"
        )
        lines.append("")
        return "\n".join(lines)

    lines.append(f"**Total endpoints:** {report.total_endpoints}")
    lines.append("")
    lines.append("| Method | Path | File | Line | Framework |")
    lines.append("|---|---|---|---|---|")
    for ep in report.endpoints:
        lines.append(
            f"| `{ep.http_method}` | `{ep.path}` | `{ep.file_path}` | "
            f"{ep.line_number} | {ep.framework} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_integrations(report: DocGenerationReport) -> str:
    lines = [
        f"# Integrations — {report.app_name}",
        "",
        "> Auto-generated external dependency inventory. Each entry is a "
        "candidate for the data-pipeline modernization plan (Gap 6) and the "
        "compliance-by-design enforcer (Gap 7).",
        f"> Last generated: {report.generated_at}.",
        "",
    ]
    if not report.integrations:
        lines.append(
            "_No external integrations detected. The application may be "
            "fully self-contained, or detection patterns need refinement._"
        )
        lines.append("")
        return "\n".join(lines)

    # Group by integration type
    by_type: dict[str, list[DetectedIntegration]] = {}
    for itg in report.integrations:
        by_type.setdefault(itg.integration_type, []).append(itg)

    lines.append(f"**Total distinct integrations:** {report.total_integrations}")
    lines.append("")

    for itype, items in sorted(by_type.items()):
        lines.append(f"## {itype}")
        lines.append("")
        if items:
            lines.append(f"_{items[0].description}_")
            lines.append("")
        lines.append("| Target | File | Line |")
        lines.append("|---|---|---|")
        for itg in items[:30]:
            target = itg.target[:80].replace("|", "/")
            lines.append(f"| `{target}` | `{itg.file_path}` | {itg.line_number} |")
        if len(items) > 30:
            lines.append(f"| ... | ... | _{len(items) - 30} more_ |")
        lines.append("")
    return "\n".join(lines)


# ── Public entry point ────────────────────────────────────────────────────


def generate_docs(
    app_name: str,
    app_path: str,
    *,
    write_to_disk: bool = False,
    output_dir: str | None = None,
    overwrite: bool = False,
) -> DocGenerationReport:
    """Walk the repo at ``app_path`` and produce a documentation bundle.

    Args:
        app_name: human-readable name used as doc title
        app_path: filesystem path to walk
        write_to_disk: if True, write the rendered files to ``output_dir``
            (or to ``<app_path>/docs/`` if no output_dir given). The
            report.files dict always contains the rendered content
            regardless of this flag.
        output_dir: target directory for the written files (optional)
        overwrite: if True, existing files in ``output_dir`` are replaced.
            Default is to refuse to overwrite and append a warning.

    Returns:
        DocGenerationReport with all detected facts + rendered file
        contents. See ``DocGenerationReport.to_dict`` for the JSON shape.

    Raises:
        FileNotFoundError: if ``app_path`` does not exist.
    """
    root = Path(app_path)
    if not root.exists():
        raise FileNotFoundError(f"App path does not exist: {app_path}")

    now = datetime.now(timezone.utc).isoformat()
    report = DocGenerationReport(
        app_name=app_name,
        app_path=app_path,
        generated_at=now,
    )

    # Analysis passes
    report.stack_scores = _detect_stack(root)
    report.primary_stack = _top_stack_tags(report.stack_scores, n=5)
    report.entry_points = _detect_entry_points(root)
    report.endpoints = _detect_endpoints(root)
    report.integrations = _detect_integrations(root)
    report.modules = _inventory_modules(root)

    # Rendering passes
    report.files = {
        "README.md": _render_readme(report),
        "ARCHITECTURE.md": _render_architecture(report),
        "ADR-0001-initial-architecture.md": _render_adr(report),
        "RUNBOOK.md": _render_runbook(report),
        "API.md": _render_api(report),
        "INTEGRATIONS.md": _render_integrations(report),
    }

    # Optional disk write
    if write_to_disk:
        out = Path(output_dir) if output_dir else (root / "docs")
        out.mkdir(parents=True, exist_ok=True)
        for filename, content in report.files.items():
            target = out / filename
            if target.exists() and not overwrite:
                report.warnings.append(
                    f"Refused to overwrite existing {target.relative_to(root) if out.is_relative_to(root) else target}. "
                    f"Pass overwrite=True to replace."
                )
                continue
            try:
                target.write_text(content, encoding="utf-8")
                report.written_to_disk.append(str(target))
            except OSError as exc:
                report.warnings.append(f"Failed to write {target}: {exc}")

    return report
