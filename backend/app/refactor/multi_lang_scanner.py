"""Multi-language vulnerability scanner — Phase 3 Gap 1.

Extends the refactor engine's detection surface beyond C# to cover the
other languages that appear in enterprise legacy codebases: Python,
VB.NET, Java, PHP. Unlike ``csharp_analyzer`` which also does deep
structural analysis (controllers, project references, cyclomatic
complexity), this module focuses strictly on line-level vulnerability
pattern detection, which is the main signal needed for the remediation
triage pipeline.

Architecture:
- ``LanguageRules`` holds the regex pattern sets for one language
- ``MultiLangScanner`` walks a repository, applies the relevant rule set
  per file extension, and emits ``ScanFinding`` objects
- ``scan()`` returns a ``ScanReport`` compatible with the triage engine's
  expected input shape

MVP coverage: Python (complete), VB.NET (SQLi + creds + crypto).
Follow-ups: Java, PHP, TypeScript.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# ── Common Finding shape ────────────────────────────────────────────────────


@dataclass
class ScanFinding:
    """A single vulnerability detection.

    Intentionally compatible in spirit with ``CSharpFinding`` so the
    triage engine can consume both without branching.
    """

    severity: str  # critical, high, medium, low
    category: str  # sql_injection, hardcoded_cred, weak_crypto, suppressed_exception, command_injection, info_leak
    title: str
    description: str
    file_path: str
    line_number: int
    language: str
    code_snippet: str = ""
    fix_suggestion: str = ""


@dataclass
class LanguageReport:
    language: str
    files_scanned: int = 0
    lines_scanned: int = 0
    findings: list[ScanFinding] = field(default_factory=list)

    def count_by_category(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.category] = out.get(f.category, 0) + 1
        return out

    def count_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out


@dataclass
class ScanReport:
    root: str
    languages: dict[str, LanguageReport] = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def total_findings(self) -> int:
        return sum(len(r.findings) for r in self.languages.values())

    @property
    def total_files(self) -> int:
        return sum(r.files_scanned for r in self.languages.values())

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "duration_ms": self.duration_ms,
            "total_files": self.total_files,
            "total_findings": self.total_findings,
            "languages": {
                lang: {
                    "files_scanned": r.files_scanned,
                    "lines_scanned": r.lines_scanned,
                    "findings_count": len(r.findings),
                    "by_category": r.count_by_category(),
                    "by_severity": r.count_by_severity(),
                    "findings": [
                        {
                            "severity": f.severity,
                            "category": f.category,
                            "title": f.title,
                            "file": f.file_path,
                            "line": f.line_number,
                            "snippet": f.code_snippet[:120],
                            "fix": f.fix_suggestion,
                        }
                        for f in r.findings[:200]  # cap for JSON payloads
                    ],
                }
                for lang, r in self.languages.items()
            },
        }


# ── Language rule sets ──────────────────────────────────────────────────────


@dataclass
class Rule:
    pattern: re.Pattern[str]
    severity: str
    category: str
    title: str
    fix: str


def _compile(rules: list[tuple[str, str, str, str, str]]) -> list[Rule]:
    return [
        Rule(
            pattern=re.compile(pat, re.IGNORECASE),
            severity=sev,
            category=cat,
            title=title,
            fix=fix,
        )
        for (pat, sev, cat, title, fix) in rules
    ]


# ── Python rules ────────────────────────────────────────────────────────────

PYTHON_RULES = _compile([
    # SQL injection — f-string with SELECT/UPDATE/DELETE/INSERT
    (
        r'''(?:cursor\.)?execute\s*\(\s*f["'](?:SELECT|INSERT|UPDATE|DELETE)''',
        "critical",
        "sql_injection",
        "SQL injection via f-string in execute()",
        "Use parameterized query: cursor.execute(query, (param1, param2))",
    ),
    (
        r'''(?:query|sql|stmt|q)\s*=\s*f["'](?:SELECT|INSERT|UPDATE|DELETE)''',
        "critical",
        "sql_injection",
        "SQL injection via f-string assignment",
        "Use parameterized query with placeholders",
    ),
    # SQL injection — % formatting
    (
        r'''["'](?:SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*%\s*''',
        "critical",
        "sql_injection",
        "SQL injection via % string formatting",
        "Use parameterized query: cursor.execute(sql, (param,))",
    ),
    # SQL injection — .format()
    (
        r'''["'](?:SELECT|INSERT|UPDATE|DELETE)[^"']*["']\.format\(''',
        "critical",
        "sql_injection",
        "SQL injection via .format()",
        "Use parameterized query with ? or %s placeholders",
    ),
    # SQL injection — string concatenation
    (
        r'''["'](?:SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\+\s*(?:str\()?''',
        "critical",
        "sql_injection",
        "SQL injection via string concatenation",
        "Never concatenate user input into SQL. Use cursor.execute(sql, params)",
    ),
    # Hardcoded credentials — common variable names with literal values
    (
        r'''(?:DB_PASSWORD|DATABASE_PASSWORD|DB_PWD|DATABASE_PWD)\s*=\s*["'][^"']{3,}["']''',
        "critical",
        "hardcoded_cred",
        "Hardcoded database password",
        "Read from os.environ or a secrets manager",
    ),
    (
        r'''(?:API_KEY|APIKEY|SECRET_KEY|SECRETKEY)\s*=\s*["'][^"']{8,}["']''',
        "critical",
        "hardcoded_cred",
        "Hardcoded API key",
        "Use os.environ.get('API_KEY') or AWS Secrets Manager",
    ),
    (
        r'''JWT_SECRET\s*=\s*["'][^"']{5,}["']''',
        "critical",
        "hardcoded_cred",
        "Hardcoded JWT secret",
        "Use environment variable and rotate regularly",
    ),
    (
        r'''SMTP_PASS\s*=\s*["'][^"']{3,}["']''',
        "critical",
        "hardcoded_cred",
        "Hardcoded SMTP password",
        "Use environment variable or secrets manager",
    ),
    (
        r'''DATABASE_URL\s*=\s*["'][^"']*:[^"']*@[^"']*["']''',
        "critical",
        "hardcoded_cred",
        "Hardcoded database URL with credentials",
        "Read DATABASE_URL from environment",
    ),
    (
        r'''(?:password|pwd|passwd|token)\s*=\s*["'][^"']{5,}["']''',
        "high",
        "hardcoded_cred",
        "Possible hardcoded password/token",
        "Move sensitive values to env vars",
    ),
    # Weak crypto
    (
        r"hashlib\.md5\s*\(",
        "high",
        "weak_crypto",
        "Weak hash: MD5",
        "Use hashlib.sha256() or bcrypt for passwords",
    ),
    (
        r"hashlib\.sha1\s*\(",
        "high",
        "weak_crypto",
        "Weak hash: SHA1",
        "Use hashlib.sha256() or better",
    ),
    (
        r"from\s+Crypto\.Cipher\s+import\s+DES",
        "high",
        "weak_crypto",
        "Weak cipher: DES",
        "Use AES-256-GCM from cryptography.hazmat",
    ),
    # Command injection
    (
        r'''(?:os\.system|subprocess\.(?:call|Popen|run))\s*\(\s*(?:["'][^"']*["']\s*\+|f["'])''',
        "critical",
        "command_injection",
        "Command injection via shell concatenation or f-string",
        "Use subprocess with a list argv and shell=False",
    ),
    (
        r"shell\s*=\s*True",
        "medium",
        "command_injection",
        "subprocess called with shell=True",
        "Avoid shell=True; pass arguments as a list",
    ),
    # Suppressed exceptions (bare except + pass)
    (
        r"except\s*(?:Exception)?\s*:\s*(?:#.*)?$",
        "low",
        "suppressed_exception",
        "Bare except — may suppress errors silently",
        "Catch specific exceptions and log them",
    ),
    # Info leak — print of exception
    (
        r"(?:print|logger\.error)\s*\(\s*(?:str\()?(?:e|exc|exception)\.(?:args|traceback)",
        "medium",
        "info_leak",
        "Exception details logged/printed verbatim",
        "Log generic message; capture details server-side only",
    ),
])


# ── VB.NET rules ────────────────────────────────────────────────────────────

VBNET_RULES = _compile([
    (
        r'''"(?:SELECT|INSERT|UPDATE|DELETE)[^"]*"\s*&\s*''',
        "critical",
        "sql_injection",
        "SQL injection via VB.NET string concatenation (&)",
        "Use SqlParameter with parameterized query",
    ),
    (
        r'''\.CommandText\s*=\s*"[^"]*"\s*&''',
        "critical",
        "sql_injection",
        "SQL injection in CommandText assignment",
        "Use SqlParameter objects",
    ),
    (
        r'''(?:Password|Pwd|Passwd)\s*=\s*"[^"]{3,}"''',
        "critical",
        "hardcoded_cred",
        "Hardcoded password",
        "Use ConfigurationManager.AppSettings or Azure Key Vault",
    ),
    (
        r'''(?:ApiKey|Api_Key|SecretKey)\s*=\s*"[^"]{8,}"''',
        "critical",
        "hardcoded_cred",
        "Hardcoded API key",
        "Use secrets manager",
    ),
    (
        r"MD5\.Create\(\)|New\s+MD5CryptoServiceProvider",
        "high",
        "weak_crypto",
        "Weak hash: MD5",
        "Use SHA256 or better",
    ),
    (
        r"SHA1\.Create\(\)|New\s+SHA1CryptoServiceProvider",
        "high",
        "weak_crypto",
        "Weak hash: SHA1",
        "Use SHA256 or better",
    ),
    (
        r"Catch\s+(?:ex\s+As\s+)?Exception\s*(?:\n|$)(?:\s*'\s*\n|\s*End\s+Try)",
        "low",
        "suppressed_exception",
        "Suppressed exception in VB.NET",
        "Log the exception before swallowing",
    ),
])


# ── Language registry ──────────────────────────────────────────────────────


@dataclass
class LanguageSpec:
    name: str
    extensions: tuple[str, ...]
    rules: list[Rule]
    skip_dir_fragments: tuple[str, ...] = (
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "bin/",
        "obj/",
        "build/",
        "dist/",
        ".git",
    )


LANGUAGE_REGISTRY: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        name="python",
        extensions=(".py",),
        rules=PYTHON_RULES,
    ),
    "vbnet": LanguageSpec(
        name="vbnet",
        extensions=(".vb",),
        rules=VBNET_RULES,
    ),
}


# ── Scanner ─────────────────────────────────────────────────────────────────


class MultiLangScanner:
    """Walk a project root and apply per-language vulnerability rules."""

    def __init__(self, root: str | Path, languages: Iterable[str] | None = None):
        self.root = Path(root)
        if languages is None:
            self.languages = list(LANGUAGE_REGISTRY.keys())
        else:
            self.languages = [lang for lang in languages if lang in LANGUAGE_REGISTRY]

    def scan(self) -> ScanReport:
        start = time.monotonic()
        report = ScanReport(root=str(self.root))

        for lang_key in self.languages:
            spec = LANGUAGE_REGISTRY[lang_key]
            lang_report = LanguageReport(language=lang_key)
            self._scan_language(spec, lang_report)
            report.languages[lang_key] = lang_report

        report.duration_ms = int((time.monotonic() - start) * 1000)
        return report

    def _scan_language(self, spec: LanguageSpec, report: LanguageReport) -> None:
        for ext in spec.extensions:
            for file_path in self.root.rglob(f"*{ext}"):
                rel = str(file_path.relative_to(self.root)).replace("\\", "/")
                if any(frag in rel for frag in spec.skip_dir_fragments):
                    continue
                self._scan_file(spec, file_path, rel, report)

    def _scan_file(
        self,
        spec: LanguageSpec,
        file_path: Path,
        rel_path: str,
        report: LanguageReport,
    ) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Failed to read %s: %s", file_path, exc)
            return

        lines = content.splitlines()
        report.files_scanned += 1
        report.lines_scanned += len(lines)

        for line_no, line in enumerate(lines, 1):
            for rule in spec.rules:
                if rule.pattern.search(line):
                    report.findings.append(
                        ScanFinding(
                            severity=rule.severity,
                            category=rule.category,
                            title=rule.title,
                            description=rule.fix,
                            file_path=rel_path,
                            line_number=line_no,
                            language=spec.name,
                            code_snippet=line.strip()[:160],
                            fix_suggestion=rule.fix,
                        )
                    )


# ── Convenience functions ──────────────────────────────────────────────────


async def scan_repository(
    root: str | Path,
    languages: Iterable[str] | None = None,
) -> ScanReport:
    """Async wrapper for consistency with the rest of the refactor engine."""
    scanner = MultiLangScanner(root, languages)
    return scanner.scan()
