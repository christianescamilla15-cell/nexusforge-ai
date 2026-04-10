"""COBOL scanner (Gap 2 from the vision doc).

Mainframe COBOL programs almost never get rewritten in modernization
programs — they get wrapped. This scanner walks a project tree looking
for .cob / .cbl / .jcl files, extracts the structural metadata a
wrapper generator needs (PROGRAM-ID, file selections, working storage
constants, procedure entry points), and surfaces the hardcoded
patterns that make mainframe code risky: DSN / password strings in
WORKING-STORAGE, hardcoded dataset names in FILE-CONTROL, Y2K-style
date pictures, missing error handlers.

The output is intentionally structured so the companion
``cobol_wrapper_generator`` module can consume it and emit a FastAPI
wrapper that exposes each program as a REST endpoint without
touching the COBOL source.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────────────


@dataclass
class CobolFinding:
    severity: str  # critical / high / medium / low
    category: str  # hardcoded_cred / hardcoded_dataset / y2k_date / no_error_handler / large_pic_width
    title: str
    description: str
    file_path: str
    line_number: int
    snippet: str = ""
    fix_suggestion: str = ""


@dataclass
class CobolFileBinding:
    """A FILE-CONTROL SELECT entry: logical name + physical assignment."""

    logical_name: str
    physical_path: str
    organization: str = "sequential"  # sequential / indexed / relative
    access_mode: str = "sequential"  # sequential / random / dynamic


@dataclass
class CobolProgram:
    program_id: str
    file_path: str
    lines_of_code: int = 0
    author: str = ""
    date_written: str = ""
    files: list[CobolFileBinding] = field(default_factory=list)
    working_storage_constants: list[str] = field(default_factory=list)
    has_error_handler: bool = False
    has_stop_run: bool = True
    referenced_copybooks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "program_id": self.program_id,
            "file_path": self.file_path,
            "lines_of_code": self.lines_of_code,
            "author": self.author,
            "date_written": self.date_written,
            "files": [
                {
                    "logical_name": f.logical_name,
                    "physical_path": f.physical_path,
                    "organization": f.organization,
                    "access_mode": f.access_mode,
                }
                for f in self.files
            ],
            "working_storage_constants": self.working_storage_constants[:20],
            "has_error_handler": self.has_error_handler,
            "has_stop_run": self.has_stop_run,
            "referenced_copybooks": self.referenced_copybooks,
        }


@dataclass
class JclJob:
    job_name: str
    file_path: str
    steps: list[str] = field(default_factory=list)  # PGM names referenced

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "file_path": self.file_path,
            "steps": self.steps,
        }


@dataclass
class CobolScanReport:
    root: str
    programs: list[CobolProgram] = field(default_factory=list)
    jcl_jobs: list[JclJob] = field(default_factory=list)
    findings: list[CobolFinding] = field(default_factory=list)
    copybooks: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def summary(self) -> dict:
        by_cat: dict[str, int] = {}
        by_sev: dict[str, int] = {}
        for f in self.findings:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        return {
            "programs": len(self.programs),
            "jcl_jobs": len(self.jcl_jobs),
            "copybooks": len(self.copybooks),
            "total_loc": sum(p.lines_of_code for p in self.programs),
            "findings": len(self.findings),
            "findings_by_category": by_cat,
            "findings_by_severity": by_sev,
        }

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "summary": self.summary(),
            "programs": [p.to_dict() for p in self.programs],
            "jcl_jobs": [j.to_dict() for j in self.jcl_jobs],
            "copybooks": self.copybooks,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "file": f.file_path,
                    "line": f.line_number,
                    "snippet": f.snippet[:120],
                    "fix": f.fix_suggestion,
                }
                for f in self.findings[:500]
            ],
            "duration_ms": self.duration_ms,
        }


# ── Regex patterns ─────────────────────────────────────────────────────────


_PROGRAM_ID_RE = re.compile(r"^\s*PROGRAM-ID\.\s+([A-Z0-9_-]+)\s*\.", re.IGNORECASE)
_AUTHOR_RE = re.compile(r"^\s*AUTHOR\.\s+(.+?)\s*\.", re.IGNORECASE)
_DATE_WRITTEN_RE = re.compile(r"^\s*DATE-WRITTEN\.\s+(.+?)\s*\.", re.IGNORECASE)
_SELECT_RE = re.compile(
    r"^\s*SELECT\s+([A-Z0-9_-]+)\s+ASSIGN\s+TO\s+['\"]?([^'\"\s]+)['\"]?",
    re.IGNORECASE,
)
_ORGANIZATION_RE = re.compile(
    r"ORGANIZATION\s+IS\s+(SEQUENTIAL|INDEXED|RELATIVE)", re.IGNORECASE
)
_ACCESS_MODE_RE = re.compile(
    r"ACCESS\s+MODE\s+IS\s+(SEQUENTIAL|RANDOM|DYNAMIC)", re.IGNORECASE
)
_WORKING_STORAGE_START_RE = re.compile(r"^\s*WORKING-STORAGE\s+SECTION", re.IGNORECASE)
_PROCEDURE_DIVISION_RE = re.compile(r"^\s*PROCEDURE\s+DIVISION", re.IGNORECASE)
_STOP_RUN_RE = re.compile(r"\bSTOP\s+RUN\b", re.IGNORECASE)
_COPY_RE = re.compile(r"^\s*COPY\s+([A-Z0-9_-]+)", re.IGNORECASE)
_ERROR_HANDLER_RE = re.compile(
    r"\b(ON\s+EXCEPTION|USE\s+.*\s+PROCEDURE|DECLARATIVES)\b", re.IGNORECASE
)

# Finding patterns
_CRED_VALUE_RE = re.compile(
    r"VALUE\s+['\"]([^'\"]*(?:PWD|PASSWORD|PASS|USER|DSN|UID)[^'\"]*)['\"]",
    re.IGNORECASE,
)
_Y2K_DATE_RE = re.compile(r"PIC\s+(?:9\(6\)|X\(6\))", re.IGNORECASE)
_LARGE_PIC_RE = re.compile(r"PIC\s+X\((\d{4,})\)", re.IGNORECASE)
_JCL_JOB_RE = re.compile(r"^//(\S+)\s+JOB\b", re.IGNORECASE)
_JCL_EXEC_RE = re.compile(r"^//\S+\s+EXEC\s+PGM=([A-Z0-9_-]+)", re.IGNORECASE)


# ── Scanner ────────────────────────────────────────────────────────────────


_COBOL_EXTENSIONS = (".cob", ".cbl", ".cpy")
_JCL_EXTENSIONS = (".jcl",)
_SKIP_DIRS = ("node_modules", "__pycache__", ".git", "bin", "obj", "dist", "build")


class CobolScanner:
    """Walk a project root and extract COBOL/JCL structural metadata."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def scan(self) -> CobolScanReport:
        start = time.monotonic()
        report = CobolScanReport(root=str(self.root))

        for fpath in self._iter_files():
            rel = str(fpath.relative_to(self.root)).replace("\\", "/")
            ext = fpath.suffix.lower()
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            if ext in _COBOL_EXTENSIONS:
                self._scan_cobol_file(rel, text, report)
            elif ext in _JCL_EXTENSIONS:
                self._scan_jcl_file(rel, text, report)

        report.duration_ms = int((time.monotonic() - start) * 1000)
        return report

    def _iter_files(self) -> Iterable[Path]:
        for fpath in self.root.rglob("*"):
            if not fpath.is_file():
                continue
            if any(part in _SKIP_DIRS for part in fpath.parts):
                continue
            if fpath.suffix.lower() in _COBOL_EXTENSIONS + _JCL_EXTENSIONS:
                yield fpath

    def _scan_cobol_file(
        self, rel_path: str, text: str, report: CobolScanReport
    ) -> None:
        is_copybook = rel_path.lower().endswith(".cpy")
        if is_copybook:
            report.copybooks.append(rel_path)

        program: CobolProgram | None = None
        current_select: CobolFileBinding | None = None
        in_working_storage = False
        lines = text.splitlines()

        for line_no, raw in enumerate(lines, 1):
            line = raw.rstrip()

            # Program header
            pid_match = _PROGRAM_ID_RE.match(line)
            if pid_match:
                if program is not None:
                    report.programs.append(program)
                program = CobolProgram(
                    program_id=pid_match.group(1),
                    file_path=rel_path,
                )
                continue

            if program is None:
                # Still parse copybook-level metadata even without PROGRAM-ID
                continue

            program.lines_of_code += 1

            m = _AUTHOR_RE.match(line)
            if m:
                program.author = m.group(1).strip()

            m = _DATE_WRITTEN_RE.match(line)
            if m:
                program.date_written = m.group(1).strip()

            m = _COPY_RE.match(line)
            if m:
                program.referenced_copybooks.append(m.group(1))

            # SELECT + continuation lines
            sel_match = _SELECT_RE.match(line)
            if sel_match:
                current_select = CobolFileBinding(
                    logical_name=sel_match.group(1),
                    physical_path=sel_match.group(2),
                )
                program.files.append(current_select)
                # Path-as-constant is a hardcoded dataset finding
                report.findings.append(
                    CobolFinding(
                        severity="medium",
                        category="hardcoded_dataset",
                        title="Hardcoded dataset path in FILE-CONTROL",
                        description=(
                            "Dataset path is embedded in the SELECT clause. "
                            "Parametrize via JCL DD statements or a runtime "
                            "lookup when wrapping this program."
                        ),
                        file_path=rel_path,
                        line_number=line_no,
                        snippet=line.strip()[:160],
                        fix_suggestion=(
                            "Replace hardcoded path with a DD name and resolve "
                            "at runtime via JCL or the wrapper's environment."
                        ),
                    )
                )
            if current_select is not None:
                org = _ORGANIZATION_RE.search(line)
                if org:
                    current_select.organization = org.group(1).lower()
                acc = _ACCESS_MODE_RE.search(line)
                if acc:
                    current_select.access_mode = acc.group(1).lower()

            # Section tracking
            if _WORKING_STORAGE_START_RE.match(line):
                in_working_storage = True
                continue
            if _PROCEDURE_DIVISION_RE.match(line):
                in_working_storage = False
                continue

            if in_working_storage:
                cred_match = _CRED_VALUE_RE.search(line)
                if cred_match:
                    program.working_storage_constants.append(line.strip())
                    report.findings.append(
                        CobolFinding(
                            severity="critical",
                            category="hardcoded_cred",
                            title="Hardcoded credential in WORKING-STORAGE",
                            description=(
                                "Connection strings or passwords embedded as "
                                "COBOL VALUE literals. These are compiled into "
                                "the load module and cannot be rotated without "
                                "recompiling."
                            ),
                            file_path=rel_path,
                            line_number=line_no,
                            snippet=line.strip()[:160],
                            fix_suggestion=(
                                "Move credentials to the wrapper layer and pass "
                                "them to the COBOL program via environment DDs."
                            ),
                        )
                    )

            # Findings applicable anywhere in the program
            if _Y2K_DATE_RE.search(line) and "DATE" in line.upper():
                report.findings.append(
                    CobolFinding(
                        severity="medium",
                        category="y2k_date",
                        title="6-digit date picture (Y2K / Y2.1K risk)",
                        description=(
                            "Dates stored as 6 digits cannot represent years "
                            "beyond 2099 without re-interpretation logic."
                        ),
                        file_path=rel_path,
                        line_number=line_no,
                        snippet=line.strip()[:160],
                        fix_suggestion=(
                            "Expand the wrapper interface to use ISO-8601 "
                            "strings and convert on the way into the COBOL "
                            "program."
                        ),
                    )
                )

            large = _LARGE_PIC_RE.search(line)
            if large:
                width = int(large.group(1))
                report.findings.append(
                    CobolFinding(
                        severity="low",
                        category="large_pic_width",
                        title=f"Unusually wide PIC ({width} chars)",
                        description=(
                            "Very wide fixed-width fields usually carry "
                            "multiple logical columns crammed together. "
                            "Split them in the wrapper's response model."
                        ),
                        file_path=rel_path,
                        line_number=line_no,
                        snippet=line.strip()[:160],
                        fix_suggestion=(
                            "Document the column layout and expose structured "
                            "sub-fields from the wrapper."
                        ),
                    )
                )

            if _ERROR_HANDLER_RE.search(line):
                program.has_error_handler = True

        # Final program
        if program is not None:
            if not program.has_error_handler:
                report.findings.append(
                    CobolFinding(
                        severity="high",
                        category="no_error_handler",
                        title="No USE PROCEDURE / ON EXCEPTION handler",
                        description=(
                            "Program has no declarative error handler or ON "
                            "EXCEPTION clause. Any runtime error aborts the "
                            "batch and leaves the output file half-written."
                        ),
                        file_path=rel_path,
                        line_number=0,
                        snippet="",
                        fix_suggestion=(
                            "Wrap invocations with a retry/rollback loop at "
                            "the JCL or wrapper layer."
                        ),
                    )
                )
            if not _STOP_RUN_RE.search(text):
                program.has_stop_run = False
            report.programs.append(program)

    def _scan_jcl_file(
        self, rel_path: str, text: str, report: CobolScanReport
    ) -> None:
        job_name: str | None = None
        steps: list[str] = []
        for raw in text.splitlines():
            line = raw.rstrip()
            m = _JCL_JOB_RE.match(line)
            if m:
                job_name = m.group(1)
            m = _JCL_EXEC_RE.match(line)
            if m:
                steps.append(m.group(1))
        if job_name:
            report.jcl_jobs.append(
                JclJob(job_name=job_name, file_path=rel_path, steps=steps)
            )


async def scan_cobol(root: str | Path) -> CobolScanReport:
    """Async wrapper for consistency with the rest of the refactor engine."""
    return CobolScanner(root).scan()
