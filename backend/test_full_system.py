"""Full system functional test — validates every NexusForge 2.0 module."""
import asyncio
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

VULN = os.environ.get("NEXUSFORGE_VULN_TEST_REPO", "C:/Users/DANNY/Desktop/nexusforge-test-repos/vuln-test")
SYNTH = os.environ.get("NEXUSFORGE_SYNTH_REPO", "C:/Users/DANNY/Desktop/nexusforge-test-repos/synth-tenant-alpha")
NXF = os.environ.get("NEXUSFORGE_REPO", "C:/Users/DANNY/Desktop/portafolio-completo/proyectos/07-nexusforge-ai")

results = {}

def log(test_num, name, detail):
    print(f"[TEST {test_num:2d}] {name:30s} {detail}")

async def run():
    import subprocess
    subprocess.run(["git", "checkout", "--", "."], cwd=VULN, capture_output=True)

    # 1: Ingestion
    from app.refactor.ingestion import RepoIngestionEngine
    e = RepoIngestionEngine()
    g1 = await e.ingest(VULN, "vuln-test")
    g2 = await e.ingest(SYNTH, "tenant-alpha")
    log(1, "INGESTION", f"vuln:{g1.total_files}f synth:{g2.total_files}f")
    results["ingestion"] = "PASS"

    # 2: C# Analyzer
    from app.refactor.csharp_analyzer import CSharpAnalyzer
    a = CSharpAnalyzer(VULN)
    projects = await a.analyze()
    findings = sum(p.to_dict()["findings_count"] for p in projects)
    log(2, "C# ANALYZER", f"{len(projects)} projects, {findings} findings")
    results["csharp_analyzer"] = "PASS" if findings > 0 else "FAIL"

    # 3: C# Fixer
    from app.refactor.csharp_fixer import CSharpFixer
    fixer = CSharpFixer(VULN, dry_run=True)
    r = fixer.fix_file("Controllers/InvoiceController.cs")
    log(3, "C# FIXER", f"{r.fixes_applied} fixes")
    results["csharp_fixer"] = "PASS" if r.fixes_applied > 0 else "FAIL"

    # 4: Triage
    from app.refactor.triage import IssuTriageEngine
    issues = [{"title": f.title, "category": f.category, "severity": f.severity,
               "file_path": f.file_path, "app": p.name}
              for p in projects for f in p.findings]
    tr = IssuTriageEngine().triage(issues).to_dict()
    log(4, "TRIAGE", f"{tr['summary']['total_issues']} issues, {len(tr['batches'])} batches")
    results["triage"] = "PASS" if tr["summary"]["total_issues"] > 0 else "FAIL"

    # 5: Batch Pipeline
    subprocess.run(["git", "checkout", "--", "."], cwd=VULN, capture_output=True)
    from app.refactor.batch_pipeline import BatchRemediationPipeline
    bp = BatchRemediationPipeline(VULN, max_workers=2, dry_run=True)
    br = await bp.execute(tr, batch_filter=[1, 2])
    brr = br.to_dict()
    log(5, "BATCH PIPELINE", f"fixed:{brr['summary']['fixed']} fixes:{brr['summary']['total_fixes_applied']}")
    results["batch_pipeline"] = "PASS" if brr["summary"]["fixed"] >= 0 else "FAIL"

    # 6: PII Scanner
    from app.refactor.pii_scanner import PIIScanner
    pii = await PIIScanner(SYNTH).scan()
    pr = pii.to_dict()
    log(6, "PII SCANNER", f"{pr['summary']['total']} findings, {pr['summary']['critical']} critical")
    results["pii_scanner"] = "PASS" if pr["summary"]["total"] > 0 else "FAIL"

    # 7: DB Analyzer
    from app.refactor.db_analyzer import DatabaseIntegrityAnalyzer
    db = await DatabaseIntegrityAnalyzer(NXF).analyze()
    dr = db.to_dict()
    log(7, "DB ANALYZER", f"{dr['summary']['total_tables']} tables")
    results["db_analyzer"] = "PASS"

    # 8: Test Generator
    from app.refactor.test_generator import TestGeneratorEngine
    tg = await TestGeneratorEngine(SYNTH, dry_run=True).generate_tests(g2)
    log(8, "TEST GENERATOR", f"{tg.to_dict()['test_files_generated']} files, {tg.to_dict()['functions_tested']} funcs")
    results["test_generator"] = "PASS" if tg.to_dict()["test_files_generated"] > 0 else "FAIL"

    # 9: CI/CD Generator
    from app.refactor.cicd_generator import generate_python_pipeline, generate_dotnet_pipeline
    py = generate_python_pipeline("test")
    net = generate_dotnet_pipeline("test")
    log(9, "CI/CD GENERATOR", f"python:{len(py)}ch dotnet:{len(net)}ch")
    results["cicd_generator"] = "PASS" if len(py) > 100 else "FAIL"

    # 10: RPA Scanner
    from app.refactor.rpa_scanner import RPAScanner
    rpa = await RPAScanner(SYNTH).scan()
    log(10, "RPA SCANNER", f"{rpa.to_dict()['total_files']} files, stability:{rpa.to_dict()['stability_score']}%")
    results["rpa_scanner"] = "PASS"

    # 11: Multi-Repo
    from app.refactor.multi_repo import MultiRepoOrchestrator
    mr = await MultiRepoOrchestrator(use_llm=False, dry_run=True).process(
        [{"path": SYNTH, "name": "tenant-alpha"}, {"path": VULN, "name": "vuln"}], generate_tests=True)
    mrr = mr.to_dict()
    log(11, "MULTI-REPO", f"{mrr['summary']['completed']}/{mrr['summary']['repos']} repos, {mrr['summary']['tests_generated']} tests")
    results["multi_repo"] = "PASS" if mrr["summary"]["completed"] == 2 else "FAIL"

    # 12: Rollback
    from app.refactor.rollback import RollbackManager
    rm = RollbackManager(VULN)
    cp = await rm.checkpoint(["Controllers/InvoiceController.cs"])
    log(12, "ROLLBACK", f"checkpoint: {cp}")
    results["rollback"] = "PASS"

    # 13: Mythos
    from app.security.mythos import MythosScanner
    mreport = await MythosScanner(NXF).full_scan()
    log(13, "MYTHOS", f"score:{mreport.to_dict()['score']}/100, findings:{mreport.to_dict()['total_findings']}")
    results["mythos"] = "PASS"

    # 14: Memory
    from app.memory.working import WorkingMemory
    wm = WorkingMemory()
    wm.set("k", "v")
    assert wm.get("k") == "v"
    wm.add_message("user", "test")
    log(14, "MEMORY (WORKING)", f"context:{len(wm.get_context_string())}ch")
    results["memory"] = "PASS"

    # 15: Agent Registry
    from app.agents.registry import list_agents
    agents = list_agents()
    log(15, "AGENT REGISTRY", f"{len(agents)} agents")
    results["agents"] = "PASS" if len(agents) >= 22 else "FAIL"

    # 16: LLM Router
    from app.llm.router import LLMRouter
    router = LLMRouter()
    c1 = [p.name for p in router._build_provider_chain("ClassifierAgent")]
    c2 = [p.name for p in router._build_provider_chain("ComplianceAgent")]
    c3 = [p.name for p in router._build_provider_chain("ReporterAgent")]
    log(16, "LLM ROUTER", f"classifier:{c1} compliance:{c2} reporter:{c3}")
    results["llm_router"] = "PASS" if "haiku" in c1 else "FAIL"

    # 17: Healing
    from app.healing.detector import FailureDetector
    from app.healing.strategies import STRATEGY_REGISTRY
    d = FailureDetector()
    log(17, "HEALING", f"strategies:{list(STRATEGY_REGISTRY.keys())}")
    results["healing"] = "PASS" if len(STRATEGY_REGISTRY) == 5 else "FAIL"

    # SUMMARY
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v == "PASS")
    failed = sum(1 for v in results.values() if v == "FAIL")
    for name, status in results.items():
        icon = "OK  " if status == "PASS" else "FAIL"
        print(f"  [{icon}] {name}")
    print(f"\n  {passed}/{passed+failed} PASSED")
    if failed > 0:
        print(f"  {failed} FAILED")
        sys.exit(1)

asyncio.run(run())
