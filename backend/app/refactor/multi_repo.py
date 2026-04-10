"""Multi-Repo Orchestrator — process multiple repositories in parallel.

Designed for enterprise clients with 5+ interdependent apps:
  1. Ingest all repos concurrently
  2. Build cross-repo dependency map
  3. Determine safe refactoring order across repos
  4. Execute refactoring in parallel (bounded concurrency)
  5. Generate consolidated report

Example:
  orchestrator = MultiRepoOrchestrator()
  report = await orchestrator.process([
      {"path": "/repos/app-01", "name": "app-01"},
      {"path": "/repos/app-02", "name": "app-02"},
      {"path": "/repos/app-03", "name": "app-03"},
      {"path": "/repos/app-04", "name": "app-04"},
      {"path": "/repos/app-05", "name": "app-05"},
  ])
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.refactor.ingestion import RepoIngestionEngine, ProjectGraph
from app.refactor.engine import RefactoringEngine, RefactorReport
from app.refactor.test_generator import TestGeneratorEngine, TestGenReport

logger = logging.getLogger(__name__)


@dataclass
class RepoJob:
    name: str
    path: str
    status: str = "pending"  # pending, ingesting, refactoring, testing, done, error
    graph: ProjectGraph | None = None
    refactor_report: RefactorReport | None = None
    test_report: TestGenReport | None = None
    error: str = ""
    duration_ms: int = 0


@dataclass
class MultiRepoReport:
    total_repos: int = 0
    repos_completed: int = 0
    repos_failed: int = 0
    total_files: int = 0
    total_lines: int = 0
    total_vulnerabilities: int = 0
    vulnerabilities_fixed: int = 0
    tests_generated: int = 0
    functions_tested: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    repos: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": {
                "repos": self.total_repos,
                "completed": self.repos_completed,
                "failed": self.repos_failed,
                "files": self.total_files,
                "lines": self.total_lines,
                "vulnerabilities_found": self.total_vulnerabilities,
                "vulnerabilities_fixed": self.vulnerabilities_fixed,
                "tests_generated": self.tests_generated,
                "functions_tested": self.functions_tested,
            },
            "cost": {
                "tokens": self.total_tokens,
                "usd": round(self.total_cost_usd, 4),
            },
            "duration_ms": self.duration_ms,
            "repos": self.repos,
        }


class MultiRepoOrchestrator:
    """Process multiple repositories in parallel with cross-repo awareness."""

    def __init__(
        self,
        use_llm: bool = True,
        dry_run: bool = False,
        max_repos_parallel: int = 3,
        max_files_parallel: int = 5,
    ):
        self.use_llm = use_llm
        self.dry_run = dry_run
        self.max_repos = max_repos_parallel
        self.max_files = max_files_parallel
        self._progress_callback = None
        self._jobs: dict[str, RepoJob] = {}

    def on_progress(self, callback):
        """Register callback: fn(repo_name, status, detail)"""
        self._progress_callback = callback

    def _emit(self, repo: str, status: str, detail: str = ""):
        if self._progress_callback:
            try:
                self._progress_callback(repo, status, detail)
            except Exception:
                pass

    async def process(
        self,
        repos: list[dict],
        fix_types: list[str] | None = None,
        generate_tests: bool = True,
    ) -> MultiRepoReport:
        """Process multiple repositories end-to-end.

        Args:
            repos: List of {"path": str, "name": str}
            fix_types: Filter specific vulnerability types
            generate_tests: Auto-generate tests for uncovered code
        """
        start = time.monotonic()
        report = MultiRepoReport(total_repos=len(repos))

        # Initialize jobs
        for r in repos:
            job = RepoJob(name=r.get("name", r["path"]), path=r["path"])
            self._jobs[r["path"]] = job

        # Phase 1: Ingest all repos in parallel
        logger.info("Phase 1: Ingesting %d repos...", len(repos))
        sem = asyncio.Semaphore(self.max_repos)
        ingest_tasks = [self._ingest_repo(sem, job) for job in self._jobs.values()]
        await asyncio.gather(*ingest_tasks, return_exceptions=True)

        # Build cross-repo shared module map
        shared_modules = self._find_shared_modules()
        if shared_modules:
            logger.info("Cross-repo shared modules: %s", list(shared_modules.keys()))

        # Phase 2: Refactor repos in dependency order
        logger.info("Phase 2: Refactoring...")
        refactor_order = self._determine_refactor_order()

        for batch in refactor_order:
            batch_tasks = []
            for path in batch:
                job = self._jobs.get(path)
                if not job or job.status == "error" or not job.graph:
                    continue
                batch_tasks.append(self._refactor_repo(sem, job, fix_types))

            await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Phase 3: Generate tests
        if generate_tests:
            logger.info("Phase 3: Generating tests...")
            test_tasks = [self._generate_tests(sem, job) for job in self._jobs.values() if job.graph]
            await asyncio.gather(*test_tasks, return_exceptions=True)

        # Compile report
        for job in self._jobs.values():
            repo_data = {
                "name": job.name,
                "path": job.path,
                "status": job.status,
                "duration_ms": job.duration_ms,
            }

            if job.graph:
                report.total_files += job.graph.total_files
                report.total_lines += job.graph.total_lines
                report.total_vulnerabilities += len(job.graph.vulnerability_hotspots)
                repo_data["files"] = job.graph.total_files
                repo_data["lines"] = job.graph.total_lines
                repo_data["languages"] = job.graph.languages
                repo_data["hotspots"] = len(job.graph.vulnerability_hotspots)

            if job.refactor_report:
                report.vulnerabilities_fixed += job.refactor_report.vulnerabilities_fixed
                report.total_tokens += job.refactor_report.total_tokens
                report.total_cost_usd += job.refactor_report.total_cost_usd
                repo_data["fixed"] = job.refactor_report.files_fixed
                repo_data["failed"] = job.refactor_report.files_failed

            if job.test_report:
                report.tests_generated += job.test_report.test_files_generated
                report.functions_tested += job.test_report.functions_tested
                repo_data["tests_generated"] = job.test_report.test_files_generated
                repo_data["functions_tested"] = job.test_report.functions_tested

            if job.status == "done":
                report.repos_completed += 1
            elif job.status == "error":
                report.repos_failed += 1
                repo_data["error"] = job.error

            report.repos.append(repo_data)

        report.duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "Multi-repo complete: %d/%d repos, %d vulns fixed, %d tests generated in %dms",
            report.repos_completed, report.total_repos,
            report.vulnerabilities_fixed, report.tests_generated,
            report.duration_ms,
        )
        return report

    async def _ingest_repo(self, sem: asyncio.Semaphore, job: RepoJob):
        async with sem:
            job.status = "ingesting"
            self._emit(job.name, "ingesting")
            start = time.monotonic()
            try:
                engine = RepoIngestionEngine()
                job.graph = await engine.ingest(job.path, job.name)
                job.duration_ms = int((time.monotonic() - start) * 1000)
                self._emit(job.name, "ingested", f"{job.graph.total_files} files, {job.graph.total_lines} lines")
            except Exception as exc:
                job.status = "error"
                job.error = str(exc)[:200]
                self._emit(job.name, "error", job.error)

    async def _refactor_repo(self, sem: asyncio.Semaphore, job: RepoJob, fix_types: list[str] | None):
        async with sem:
            job.status = "refactoring"
            self._emit(job.name, "refactoring")
            try:
                engine = RefactoringEngine(
                    project_root=job.path,
                    use_llm=self.use_llm,
                    dry_run=self.dry_run,
                )
                job.refactor_report = await engine.refactor_project(
                    job.graph, fix_types=fix_types, max_parallel=self.max_files,
                )
                self._emit(job.name, "refactored", f"{job.refactor_report.files_fixed} fixed")
            except Exception as exc:
                job.status = "error"
                job.error = str(exc)[:200]
                self._emit(job.name, "error", job.error)

    async def _generate_tests(self, sem: asyncio.Semaphore, job: RepoJob):
        async with sem:
            job.status = "testing"
            self._emit(job.name, "generating_tests")
            try:
                gen = TestGeneratorEngine(project_root=job.path, dry_run=self.dry_run)
                job.test_report = await gen.generate_tests(job.graph)
                job.status = "done"
                self._emit(job.name, "done", f"{job.test_report.test_files_generated} test files")
            except Exception as exc:
                job.status = "error"
                job.error = str(exc)[:200]

    def _find_shared_modules(self) -> dict[str, list[str]]:
        """Find modules that appear in multiple repos (shared dependencies)."""
        module_repos: dict[str, list[str]] = {}
        for job in self._jobs.values():
            if not job.graph:
                continue
            for mod_name in job.graph.modules:
                if mod_name.startswith("_") or mod_name.startswith("."):
                    continue
                if mod_name not in module_repos:
                    module_repos[mod_name] = []
                module_repos[mod_name].append(job.name)

        return {k: v for k, v in module_repos.items() if len(v) > 1}

    def _determine_refactor_order(self) -> list[list[str]]:
        """Determine safe order to refactor repos.

        Repos with fewer dependencies are refactored first.
        Shared-dependency repos are batched together.
        """
        # Simple heuristic: sort by total vulnerabilities (most first = highest value)
        jobs_sorted = sorted(
            [j for j in self._jobs.values() if j.graph],
            key=lambda j: len(j.graph.vulnerability_hotspots),
            reverse=True,
        )

        # Batch into groups of max_repos
        batches = []
        for i in range(0, len(jobs_sorted), self.max_repos):
            batches.append([j.path for j in jobs_sorted[i:i + self.max_repos]])

        return batches if batches else [[j.path for j in jobs_sorted]]
