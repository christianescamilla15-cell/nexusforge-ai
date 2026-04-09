"""Repo Ingestion Engine — auto-discover, fingerprint, and map any codebase.

Turns a Git repo into a structured project graph:
  1. Clone or scan local directory
  2. Detect languages, frameworks, databases per file
  3. Build dependency graph (imports, shared modules)
  4. Identify vulnerability hotspots (pre-scan with patterns)
  5. Generate refactoring DAG (what to fix first)

Supports: Python, C#, Java, PHP, TypeScript, JavaScript, Go, Ruby, Cobol, VB.NET
"""

import asyncio
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Language Detection ──────────────────────────────────────────────────────

_EXT_TO_LANG = {
    ".py": "python", ".pyw": "python",
    ".cs": "csharp",
    ".java": "java",
    ".php": "php",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".go": "go",
    ".rb": "ruby",
    ".cbl": "cobol", ".cob": "cobol", ".cpy": "cobol",
    ".vb": "vbnet",
    ".sql": "sql",
    ".sh": "bash", ".bash": "bash",
    ".yml": "yaml", ".yaml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html", ".htm": "html",
    ".css": "css",
    ".md": "markdown",
    ".toml": "toml",
    ".env": "env",
}

_FRAMEWORK_PATTERNS = {
    "python": [
        (r"from fastapi|import fastapi", "FastAPI"),
        (r"from flask|import flask", "Flask"),
        (r"from django", "Django"),
        (r"import playwright", "Playwright"),
        (r"import zmq|from zmq", "ZeroMQ"),
        (r"import asyncpg|import psycopg", "PostgreSQL"),
        (r"import pymysql|import mysql", "MySQL"),
        (r"import redis", "Redis"),
        (r"import boto3", "AWS SDK"),
        (r"import anthropic", "Claude API"),
        (r"import openai", "OpenAI API"),
        (r"from sqlalchemy", "SQLAlchemy"),
        (r"import pytest", "pytest"),
    ],
    "csharp": [
        (r"using System\.Data\.SqlClient|using Microsoft\.Data\.SqlClient", "SQL Server"),
        (r"using Oracle", "Oracle"),
        (r"using MySql", "MySQL"),
        (r"using IBM\.Data\.DB2", "DB2"),
        (r"using Microsoft\.AspNetCore", "ASP.NET Core"),
        (r"using System\.Web", "ASP.NET Framework"),
    ],
    "php": [
        (r"mysqli_|new mysqli", "MySQL"),
        (r"PDO|new PDO", "PDO"),
        (r"exec\(|popen\(|system\(|shell_exec\(", "Shell Execution"),
    ],
    "typescript": [
        (r"from 'react'|from \"react\"", "React"),
        (r"from 'express'", "Express"),
        (r"from 'next'", "Next.js"),
    ],
    "java": [
        (r"import java\.sql\.", "JDBC"),
        (r"import org\.springframework", "Spring"),
        (r"import javax\.servlet", "Servlet"),
    ],
}

_IGNORE_DIRS = {
    "node_modules", "__pycache__", ".git", ".svn", "dist", "build",
    "bin", "obj", "target", ".idea", ".vscode", "vendor", "venv",
    ".env", "logs", "coverage", ".next", ".nuxt",
}

# ── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class FileInfo:
    path: str               # Relative path from repo root
    language: str
    lines: int
    size_bytes: int
    imports: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    vulnerabilities: int = 0
    complexity: str = "low"  # low, medium, high

@dataclass
class ModuleInfo:
    name: str
    path: str
    language: str
    files: list[str] = field(default_factory=list)
    frameworks: set = field(default_factory=set)
    depends_on: set = field(default_factory=set)   # Other modules this depends on
    depended_by: set = field(default_factory=set)   # Modules that depend on this
    total_lines: int = 0
    vulnerability_count: int = 0

@dataclass
class ProjectGraph:
    root: str
    name: str
    modules: dict[str, ModuleInfo] = field(default_factory=dict)
    files: list[FileInfo] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)      # lang → file count
    frameworks: dict[str, list[str]] = field(default_factory=dict)  # framework → files
    total_files: int = 0
    total_lines: int = 0
    vulnerability_hotspots: list[dict] = field(default_factory=list)
    refactor_dag: list[list[str]] = field(default_factory=list)   # Ordered groups
    scan_duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "frameworks": {k: v[:10] for k, v in self.frameworks.items()},
            "modules": {
                name: {
                    "path": m.path,
                    "language": m.language,
                    "files": len(m.files),
                    "lines": m.total_lines,
                    "frameworks": list(m.frameworks),
                    "depends_on": list(m.depends_on),
                    "depended_by": list(m.depended_by),
                    "vulnerabilities": m.vulnerability_count,
                }
                for name, m in self.modules.items()
            },
            "vulnerability_hotspots": self.vulnerability_hotspots[:20],
            "refactor_dag": self.refactor_dag,
            "scan_duration_ms": self.scan_duration_ms,
        }


# ── Vulnerability Pre-Scanner ───────────────────────────────────────────────

_VULN_PATTERNS = {
    "python": [
        (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{', "SQL injection (f-string)", "critical"),
        (r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', "SQL injection (.format)", "critical"),
        (r'(?:password|secret|api_key)\s*=\s*["\'][^"\']{5,}["\']', "Hardcoded secret", "critical"),
        (r'eval\(|exec\(', "Code injection", "critical"),
        (r'os\.system\(|subprocess.*shell\s*=\s*True', "Command injection", "high"),
        (r'verify\s*=\s*False', "SSL verification disabled", "high"),
    ],
    "csharp": [
        (r'"SELECT.*"\s*\+\s*', "SQL injection (concatenation)", "critical"),
        (r'password\s*=\s*"[^"]{3,}"', "Hardcoded password", "critical"),
        (r'Process\.Start\(', "Process execution", "medium"),
    ],
    "php": [
        (r'\$_(?:GET|POST|REQUEST)\[.*\].*(?:mysql_query|mysqli_query)', "SQL injection", "critical"),
        (r'exec\(|popen\(|system\(|shell_exec\(|passthru\(', "Command injection", "critical"),
        (r'md5\(|sha1\(', "Weak hashing", "high"),
        (r'eval\(', "Code injection", "critical"),
    ],
    "java": [
        (r'"SELECT.*"\s*\+\s*', "SQL injection (concatenation)", "critical"),
        (r'Runtime\.getRuntime\(\)\.exec\(', "Command injection", "high"),
    ],
    "typescript": [
        (r'dangerouslySetInnerHTML', "XSS risk", "high"),
        (r'eval\(', "Code injection", "critical"),
    ],
    "javascript": [
        (r'innerHTML\s*=', "XSS risk", "high"),
        (r'eval\(', "Code injection", "critical"),
        (r'document\.write\(', "XSS risk", "high"),
    ],
}

# ── Import Extraction ───────────────────────────────────────────────────────

def _extract_imports(content: str, language: str) -> list[str]:
    """Extract imported modules/packages from source code."""
    imports = []
    if language == "python":
        for m in re.finditer(r'(?:from|import)\s+([\w.]+)', content):
            imports.append(m.group(1).split('.')[0])
    elif language == "csharp":
        for m in re.finditer(r'using\s+([\w.]+)', content):
            imports.append(m.group(1).split('.')[0])
    elif language == "java":
        for m in re.finditer(r'import\s+([\w.]+)', content):
            parts = m.group(1).split('.')
            imports.append(parts[0] if len(parts) < 3 else '.'.join(parts[:2]))
    elif language in ("typescript", "javascript"):
        for m in re.finditer(r"(?:from|require\()\s*['\"]([^'\"]+)['\"]", content):
            imports.append(m.group(1))
    elif language == "php":
        for m in re.finditer(r"(?:require|include|use)\s+['\"]?([^;'\"]+)", content):
            imports.append(m.group(1))
    return list(set(imports))


# ── Main Engine ─────────────────────────────────────────────────────────────

class RepoIngestionEngine:
    """Ingest a repository and produce a ProjectGraph."""

    def __init__(self):
        self.graph: ProjectGraph | None = None

    async def ingest(self, path: str, name: str = "") -> ProjectGraph:
        """Scan an entire repository and build the project graph.

        Args:
            path: Absolute path to repo root (or Git URL to clone)
            name: Project name (auto-detected from directory if empty)
        """
        start = time.monotonic()
        root = Path(path)

        # Git clone if URL
        if path.startswith("http") or path.startswith("git@"):
            root = await self._git_clone(path)

        if not root.exists():
            raise FileNotFoundError(f"Repository not found: {path}")

        project_name = name or root.name
        graph = ProjectGraph(root=str(root), name=project_name)

        # Phase 1: Scan all files
        logger.info("Ingestion phase 1: scanning files in %s", root)
        all_files = self._scan_files(root)
        graph.files = all_files
        graph.total_files = len(all_files)
        graph.total_lines = sum(f.lines for f in all_files)

        # Language distribution
        for f in all_files:
            graph.languages[f.language] = graph.languages.get(f.language, 0) + 1

        # Framework distribution
        fw_files: dict[str, list[str]] = defaultdict(list)
        for f in all_files:
            for fw in f.frameworks:
                fw_files[fw].append(f.path)
        graph.frameworks = dict(fw_files)

        # Phase 2: Build modules (group by top-level directory)
        logger.info("Ingestion phase 2: building modules")
        graph.modules = self._build_modules(all_files, root)

        # Phase 3: Dependency graph
        logger.info("Ingestion phase 3: dependency graph")
        self._resolve_dependencies(graph)

        # Phase 4: Vulnerability hotspots
        logger.info("Ingestion phase 4: vulnerability pre-scan")
        graph.vulnerability_hotspots = self._find_hotspots(all_files)

        # Phase 5: Refactoring DAG
        logger.info("Ingestion phase 5: refactoring DAG")
        graph.refactor_dag = self._build_refactor_dag(graph)

        graph.scan_duration_ms = int((time.monotonic() - start) * 1000)
        self.graph = graph

        logger.info(
            "Ingestion complete: %d files, %d lines, %d modules, %d vulnerabilities in %dms",
            graph.total_files, graph.total_lines, len(graph.modules),
            sum(m.vulnerability_count for m in graph.modules.values()),
            graph.scan_duration_ms,
        )
        return graph

    def _scan_files(self, root: Path) -> list[FileInfo]:
        """Scan all source files in the repository."""
        files = []
        for fpath in root.rglob("*"):
            if not fpath.is_file():
                continue
            # Skip ignored directories
            if any(part in _IGNORE_DIRS for part in fpath.parts):
                continue

            ext = fpath.suffix.lower()
            lang = _EXT_TO_LANG.get(ext)
            if not lang:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                lines = content.count("\n") + 1
                rel = str(fpath.relative_to(root))

                # Detect frameworks
                frameworks = []
                if lang in _FRAMEWORK_PATTERNS:
                    for pattern, fw_name in _FRAMEWORK_PATTERNS[lang]:
                        if re.search(pattern, content):
                            frameworks.append(fw_name)

                # Extract imports
                imports = _extract_imports(content, lang)

                # Pre-scan vulnerabilities
                vuln_count = 0
                if lang in _VULN_PATTERNS:
                    for pattern, _, _ in _VULN_PATTERNS[lang]:
                        vuln_count += len(re.findall(pattern, content, re.IGNORECASE))

                # Estimate complexity
                complexity = "low"
                if lines > 500 or vuln_count > 3:
                    complexity = "high"
                elif lines > 200 or vuln_count > 0:
                    complexity = "medium"

                files.append(FileInfo(
                    path=rel,
                    language=lang,
                    lines=lines,
                    size_bytes=fpath.stat().st_size,
                    imports=imports,
                    frameworks=frameworks,
                    vulnerabilities=vuln_count,
                    complexity=complexity,
                ))
            except Exception:
                pass
        return files

    def _build_modules(self, files: list[FileInfo], root: Path) -> dict[str, ModuleInfo]:
        """Group files into logical modules by top-level directory."""
        modules: dict[str, ModuleInfo] = {}
        for f in files:
            parts = Path(f.path).parts
            # Module = first meaningful directory (skip root-level files)
            if len(parts) <= 1:
                mod_name = "_root"
                mod_path = "."
            else:
                mod_name = parts[0]
                mod_path = parts[0]

            if mod_name not in modules:
                modules[mod_name] = ModuleInfo(
                    name=mod_name,
                    path=mod_path,
                    language=f.language,
                )
            mod = modules[mod_name]
            mod.files.append(f.path)
            mod.total_lines += f.lines
            mod.frameworks.update(f.frameworks)
            mod.vulnerability_count += f.vulnerabilities
            # Track primary language (most files)
            if f.language != mod.language:
                lang_counts: dict[str, int] = defaultdict(int)
                for mf in files:
                    if Path(mf.path).parts[0] == mod_name if len(Path(mf.path).parts) > 1 else True:
                        lang_counts[mf.language] += 1
                mod.language = max(lang_counts, key=lang_counts.get, default=f.language)

        return modules

    def _resolve_dependencies(self, graph: ProjectGraph):
        """Resolve inter-module dependencies from import statements."""
        module_names = set(graph.modules.keys())
        for f in graph.files:
            parts = Path(f.path).parts
            mod_name = parts[0] if len(parts) > 1 else "_root"

            for imp in f.imports:
                imp_lower = imp.lower().replace("-", "_")
                # Check if import matches another module
                for other in module_names:
                    if other == mod_name:
                        continue
                    if imp_lower == other.lower() or imp_lower.startswith(other.lower()):
                        if mod_name in graph.modules and other in graph.modules:
                            graph.modules[mod_name].depends_on.add(other)
                            graph.modules[other].depended_by.add(mod_name)

    def _find_hotspots(self, files: list[FileInfo]) -> list[dict]:
        """Identify the most vulnerable files (prioritize fixes here)."""
        hotspots = [
            {"file": f.path, "language": f.language, "vulnerabilities": f.vulnerabilities,
             "lines": f.lines, "complexity": f.complexity}
            for f in files if f.vulnerabilities > 0
        ]
        hotspots.sort(key=lambda x: (-x["vulnerabilities"], -x["lines"]))
        return hotspots

    def _build_refactor_dag(self, graph: ProjectGraph) -> list[list[str]]:
        """Build topological order for safe refactoring.

        Modules with no dependencies are refactored first (leaf nodes).
        Shared/depended-on modules are refactored last (most impact).
        """
        # Kahn's algorithm for topological sort
        in_degree = {name: len(m.depends_on) for name, m in graph.modules.items()}
        queue = [name for name, deg in in_degree.items() if deg == 0]
        groups: list[list[str]] = []

        visited = set()
        while queue:
            # All nodes with in_degree 0 can be processed in parallel
            group = sorted(queue)
            groups.append(group)
            visited.update(group)
            next_queue = []
            for name in group:
                for dependent in graph.modules[name].depended_by:
                    if dependent in visited:
                        continue
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            queue = next_queue

        # Add any remaining (cycles) as final group
        remaining = [name for name in graph.modules if name not in visited]
        if remaining:
            groups.append(remaining)

        return groups

    async def _git_clone(self, url: str) -> Path:
        """Clone a git repo to a temp directory."""
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="nexusforge_"))
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", url, str(tmp / "repo"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Git clone failed for {url}")
        return tmp / "repo"
