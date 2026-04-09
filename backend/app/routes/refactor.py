"""Refactoring API — ingest repos, auto-fix vulnerabilities, generate PRs.

Endpoints:
  POST /refactor/ingest    — Scan and map a repository
  POST /refactor/execute   — Run automated refactoring on ingested project
  POST /refactor/pr        — Generate PR from refactoring results
  GET  /refactor/status    — Check refactoring job status
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/refactor", tags=["refactor-engine"])


class IngestRequest(BaseModel):
    path: str                          # Local path or Git URL
    name: str = ""                     # Project name

class RefactorRequest(BaseModel):
    project_path: str                  # Path to ingested project
    fix_types: list[str] | None = None # Filter: ["sql_injection", "hardcoded_secret"]
    use_llm: bool = True               # Use LLM for complex fixes
    dry_run: bool = False              # Don't modify files
    max_parallel: int = 5              # Concurrent file processing

class PRRequest(BaseModel):
    project_path: str
    base_branch: str = "main"


def _get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user.get("sub", user.get("user_id", ""))


# In-memory job storage (replace with Redis for production)
_jobs: dict[str, dict] = {}


@router.post("/ingest")
async def ingest_repo(body: IngestRequest, request: Request):
    """Ingest a repository: scan, detect languages, build dependency graph."""
    _get_user_id(request)

    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    from app.refactor.ingestion import RepoIngestionEngine

    engine = RepoIngestionEngine()
    try:
        graph = await engine.ingest(body.path, body.name)
        return graph.to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Ingestion failed")


@router.post("/execute")
async def execute_refactoring(body: RefactorRequest, request: Request):
    """Execute automated refactoring on a project.

    Processes vulnerability hotspots in DAG order with parallel execution.
    """
    _get_user_id(request)

    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    from app.refactor.ingestion import RepoIngestionEngine
    from app.refactor.engine import RefactoringEngine

    # First ingest
    ingestion = RepoIngestionEngine()
    try:
        graph = await ingestion.ingest(body.project_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {type(exc).__name__}")

    # Then refactor
    engine = RefactoringEngine(
        project_root=body.project_path,
        use_llm=body.use_llm,
        dry_run=body.dry_run,
    )

    report = await engine.refactor_project(
        graph=graph,
        fix_types=body.fix_types,
        max_parallel=body.max_parallel,
    )

    # Store result for PR generation
    _jobs[body.project_path] = {
        "graph": graph.to_dict(),
        "report": report.to_dict(),
    }

    return report.to_dict()


@router.post("/pr")
async def generate_pr(body: PRRequest, request: Request):
    """Generate a PR-ready branch from refactoring results."""
    _get_user_id(request)

    job = _jobs.get(body.project_path)
    if not job:
        raise HTTPException(status_code=404, detail="No refactoring results found. Run /refactor/execute first.")

    from app.refactor.pr_generator import PRGenerator
    from app.refactor.engine import RefactorReport

    generator = PRGenerator(body.project_path)

    # Reconstruct report
    report_data = job["report"]
    report = RefactorReport(project_name=report_data["project"])
    report.files_fixed = report_data["summary"]["fixed"]
    report.vulnerabilities_fixed = report_data["summary"]["vulnerabilities_fixed"]
    report.tests_passing = report_data["summary"]["tests_passing"]
    report.files_failed = report_data["summary"]["failed"]
    report.total_cost_usd = report_data["cost"]["usd"]
    report.duration_ms = report_data["duration_ms"]

    result = await generator.generate_pr(report, base_branch=body.base_branch)
    return result


class TestGenRequest(BaseModel):
    project_path: str
    languages: list[str] | None = None  # Filter: ["python", "csharp"]
    dry_run: bool = False


@router.post("/generate-tests")
async def generate_tests(body: TestGenRequest, request: Request):
    """Auto-generate test files for codebases with zero test coverage."""
    _get_user_id(request)

    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    from app.refactor.ingestion import RepoIngestionEngine
    from app.refactor.test_generator import TestGeneratorEngine

    ingestion = RepoIngestionEngine()
    try:
        graph = await ingestion.ingest(body.project_path)
    except Exception:
        raise HTTPException(status_code=400, detail="Ingestion failed")

    generator = TestGeneratorEngine(
        project_root=body.project_path,
        dry_run=body.dry_run,
    )
    report = await generator.generate_tests(graph, languages=body.languages)
    return report.to_dict()


class MultiRepoRequest(BaseModel):
    repos: list[dict]              # [{"path": str, "name": str}, ...]
    fix_types: list[str] | None = None
    use_llm: bool = True
    dry_run: bool = False
    generate_tests: bool = True
    max_repos_parallel: int = 3


@router.post("/multi-repo")
async def multi_repo_refactor(body: MultiRepoRequest, request: Request):
    """Process multiple repositories in parallel — enterprise pipeline.

    Ingests all repos, builds cross-repo dependency map,
    refactors in safe order, generates tests, and produces consolidated report.
    """
    _get_user_id(request)

    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    from app.refactor.multi_repo import MultiRepoOrchestrator

    orchestrator = MultiRepoOrchestrator(
        use_llm=body.use_llm,
        dry_run=body.dry_run,
        max_repos_parallel=body.max_repos_parallel,
    )

    report = await orchestrator.process(
        repos=body.repos,
        fix_types=body.fix_types,
        generate_tests=body.generate_tests,
    )

    return report.to_dict()


class CSharpAnalyzeRequest(BaseModel):
    project_path: str


@router.post("/analyze-csharp")
async def analyze_csharp(body: CSharpAnalyzeRequest, request: Request):
    """Deep C#/.NET analysis — classes, vulnerabilities, god classes, auth gaps."""
    _get_user_id(request)

    from app.refactor.csharp_analyzer import CSharpAnalyzer

    analyzer = CSharpAnalyzer(body.project_path)
    projects = await analyzer.analyze()
    return [p.to_dict() for p in projects]


@router.post("/fix-csharp")
async def fix_csharp(body: CSharpAnalyzeRequest, request: Request):
    """Auto-fix SQL injection and hardcoded credentials in C# files."""
    _get_user_id(request)

    from app.refactor.csharp_analyzer import CSharpAnalyzer
    from app.refactor.csharp_fixer import CSharpFixer

    # First analyze
    analyzer = CSharpAnalyzer(body.project_path)
    projects = await analyzer.analyze()

    # Then fix files with findings
    fixer = CSharpFixer(body.project_path, dry_run=True)
    results = []
    for proj in projects:
        for finding in proj.findings:
            if finding.category in ("sql_injection", "hardcoded_cred"):
                result = fixer.fix_file(finding.file_path)
                if result.fixes_applied > 0:
                    results.append({
                        "file": result.file_path,
                        "fixes": result.fixes_applied,
                        "diff": result.diff_summary,
                        "details": result.fixes,
                    })
    return {"files_fixed": len(results), "results": results}


@router.post("/generate-cicd")
async def generate_cicd(body: CSharpAnalyzeRequest, request: Request):
    """Generate GitHub Actions CI/CD pipelines for .NET and Python projects."""
    _get_user_id(request)

    from app.refactor.csharp_analyzer import CSharpAnalyzer
    from app.refactor.cicd_generator import CICDGenerator

    analyzer = CSharpAnalyzer(body.project_path)
    projects = await analyzer.analyze()

    generator = CICDGenerator(body.project_path, dry_run=True)
    results = []
    for proj in projects:
        result = generator.generate_for_project(proj)
        results.append({
            "project": proj.name,
            "pipelines": result["pipelines"],
            "test_files": len(result["test_files"]),
        })
    return {"projects": len(results), "results": results}


@router.post("/scan-rpa")
async def scan_rpa(body: CSharpAnalyzeRequest, request: Request):
    """Scan RPA code for fragile Playwright selectors and stability issues."""
    _get_user_id(request)

    from app.refactor.rpa_scanner import RPAScanner

    scanner = RPAScanner(body.project_path)
    report = await scanner.scan()
    return report.to_dict()


@router.get("/status/{project_path:path}")
async def get_status(project_path: str, request: Request):
    """Check status of a refactoring job."""
    job = _jobs.get(project_path)
    if not job:
        return {"status": "not_found"}
    return {
        "status": "completed",
        "summary": job["report"]["summary"],
        "cost": job["report"]["cost"],
    }
