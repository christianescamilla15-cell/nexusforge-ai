"""Tests for Gap 8 — AI-powered documentation generator.

Covers stack inference, entry-point detection, endpoint extraction for
4 web frameworks, integration discovery, module inventory, the 6
renderer outputs, and the end-to-end generate_docs orchestrator with
and without disk writes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.refactor.docs_generator import (
    DetectedEndpoint,
    DetectedIntegration,
    DocGenerationReport,
    EntryPoint,
    ModuleEntry,
    _detect_endpoints,
    _detect_entry_points,
    _detect_integrations,
    _detect_stack,
    _inventory_modules,
    _render_adr,
    _render_api,
    _render_architecture,
    _render_integrations,
    _render_readme,
    _render_runbook,
    _top_stack_tags,
    generate_docs,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Minimal empty repo root."""
    return tmp_path


def _write(root: Path, rel_path: str, content: str) -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ── Stack inference ──────────────────────────────────────────────────────


def test_stack_detects_python(tmp_repo: Path):
    _write(tmp_repo, "requirements.txt", "fastapi==0.100.0\n")
    _write(tmp_repo, "pyproject.toml", "[project]\nname='x'\n")
    scores = _detect_stack(tmp_repo)
    assert "python" in scores
    assert scores["python"] >= 10


def test_stack_detects_dotnet(tmp_repo: Path):
    _write(tmp_repo, "App/App.csproj", "<Project />")
    _write(tmp_repo, "App/Program.cs", "class P {}")
    _write(tmp_repo, "App/appsettings.json", "{}")
    scores = _detect_stack(tmp_repo)
    assert "dotnet" in scores or "dotnet-core" in scores


def test_stack_detects_cobol(tmp_repo: Path):
    _write(tmp_repo, "legacy/batch.cbl", "       IDENTIFICATION DIVISION.\n")
    _write(tmp_repo, "legacy/record.cpy", "01 RECORD.\n")
    scores = _detect_stack(tmp_repo)
    assert "cobol" in scores


def test_stack_detects_docker(tmp_repo: Path):
    _write(tmp_repo, "Dockerfile", "FROM python:3.12\n")
    _write(tmp_repo, "docker-compose.yml", "services:\n  app:\n")
    scores = _detect_stack(tmp_repo)
    assert "docker" in scores
    assert "docker-compose" in scores


def test_stack_skips_node_modules(tmp_repo: Path):
    _write(tmp_repo, "node_modules/pkg/package.json", '{"name":"fake"}')
    _write(tmp_repo, "src/app.py", "x=1\n")
    scores = _detect_stack(tmp_repo)
    # No 'javascript' from node_modules
    assert "javascript" not in scores


def test_top_stack_tags_orders_by_score():
    scores = {"python": 50, "docker": 10, "dotnet": 30}
    top = _top_stack_tags(scores, n=2)
    assert top == ["python", "dotnet"]


def test_top_stack_tags_empty_scores():
    assert _top_stack_tags({}, n=5) == []


# ── Entry-point detection ────────────────────────────────────────────────


def test_detect_entry_point_main_py(tmp_repo: Path):
    _write(tmp_repo, "main.py", "if __name__ == '__main__': print('hi')\n")
    eps = _detect_entry_points(tmp_repo)
    paths = [e.file_path for e in eps]
    assert "main.py" in paths


def test_detect_entry_point_dotnet_program(tmp_repo: Path):
    _write(tmp_repo, "Program.cs", "class Program {}\n")
    eps = _detect_entry_points(tmp_repo)
    paths = [e.file_path for e in eps]
    assert "Program.cs" in paths


def test_detect_entry_point_prefers_shallowest(tmp_repo: Path):
    _write(tmp_repo, "deep/nested/main.py", "")
    _write(tmp_repo, "main.py", "")
    eps = _detect_entry_points(tmp_repo)
    # Shallow main.py should appear first
    assert eps[0].file_path == "main.py"


def test_detect_entry_point_cap_eight(tmp_repo: Path):
    for i in range(20):
        _write(tmp_repo, f"app{i}/main.py", "")
    eps = _detect_entry_points(tmp_repo)
    assert len(eps) == 8


# ── Endpoint detection ──────────────────────────────────────────────────


def test_endpoint_fastapi(tmp_repo: Path):
    _write(tmp_repo, "app/main.py", """
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/users")
def create_user():
    pass
""")
    eps = _detect_endpoints(tmp_repo)
    paths = [(e.http_method, e.path) for e in eps]
    assert ("GET", "/health") in paths
    assert ("POST", "/users") in paths


def test_endpoint_flask(tmp_repo: Path):
    _write(tmp_repo, "app/views.py", """
from flask import Blueprint

bp = Blueprint('api', __name__)

@bp.route("/items")
def list_items():
    return []
""")
    eps = _detect_endpoints(tmp_repo)
    paths = [e.path for e in eps]
    assert "/items" in paths


def test_endpoint_express(tmp_repo: Path):
    _write(tmp_repo, "server.js", """
const express = require('express');
const app = express();

app.get('/orders', (req, res) => res.json([]));
app.post('/orders', (req, res) => res.json({}));
""")
    eps = _detect_endpoints(tmp_repo)
    methods = {e.http_method for e in eps if e.path == "/orders"}
    assert "GET" in methods
    assert "POST" in methods


def test_endpoint_spring_mapping(tmp_repo: Path):
    _write(tmp_repo, "src/UserController.java", """
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {
    @GetMapping("/users")
    public List<User> list() { return null; }
}
""")
    eps = _detect_endpoints(tmp_repo)
    assert any(e.path == "/users" and e.http_method == "GET" for e in eps)


def test_endpoint_dedupe(tmp_repo: Path):
    # Two files declaring the same route — should only show once
    _write(tmp_repo, "a.py", '@app.get("/dup")\ndef a(): pass')
    _write(tmp_repo, "b.py", '@app.get("/dup")\ndef b(): pass')
    eps = _detect_endpoints(tmp_repo)
    matches = [e for e in eps if e.path == "/dup"]
    assert len(matches) == 1  # deduped


def test_endpoint_empty_repo_returns_empty(tmp_repo: Path):
    assert _detect_endpoints(tmp_repo) == []


# ── Integration detection ───────────────────────────────────────────────


def test_integration_ftp(tmp_repo: Path):
    _write(tmp_repo, "src/transfer.py", """
FTP_URL = "ftp://partner.example.com/incoming"
""")
    its = _detect_integrations(tmp_repo)
    assert any(i.integration_type == "ftp" and "partner" in i.target for i in its)


def test_integration_http_endpoint(tmp_repo: Path):
    _write(tmp_repo, "src/client.py", """
BASE = "https://api.partner-service.com/v1"
""")
    its = _detect_integrations(tmp_repo)
    assert any(i.integration_type == "http" and "partner-service" in i.target for i in its)


def test_integration_database_connection_string(tmp_repo: Path):
    _write(tmp_repo, "src/db.py", """
DB_URL = "postgresql://user:pass@prod-db.example.com:5432/orders"
""")
    its = _detect_integrations(tmp_repo)
    assert any(i.integration_type == "database" for i in its)


def test_integration_skips_localhost(tmp_repo: Path):
    _write(tmp_repo, "src/test.py", """
URL = "http://localhost:8080/api"
URL2 = "http://127.0.0.1/health"
""")
    its = _detect_integrations(tmp_repo)
    # Neither localhost nor 127.* should count as an external integration
    assert not any("localhost" in i.target for i in its)
    assert not any("127." in i.target for i in its)


def test_integration_skips_schema_uris(tmp_repo: Path):
    _write(tmp_repo, "src/app.cs", """
using System.Xml;
// Schema namespace
public class Foo { string ns = "http://schemas.microsoft.com/office/2006/01/customui"; }
""")
    its = _detect_integrations(tmp_repo)
    assert not any("schemas.microsoft.com" in i.target for i in its)


def test_integration_dedupe(tmp_repo: Path):
    _write(tmp_repo, "a.py", 'x = "https://api.foo.com/v1"\n')
    _write(tmp_repo, "b.py", 'y = "https://api.foo.com/v1"\n')
    its = _detect_integrations(tmp_repo)
    foo_count = sum(1 for i in its if "api.foo.com" in i.target)
    assert foo_count == 1


# ── Module inventory ────────────────────────────────────────────────────


def test_module_inventory_counts_files(tmp_repo: Path):
    _write(tmp_repo, "src/a.py", "x=1")
    _write(tmp_repo, "src/b.py", "y=2")
    _write(tmp_repo, "tests/test_a.py", "def test(): pass")
    mods = _inventory_modules(tmp_repo)
    by_name = {m.name: m for m in mods}
    assert by_name["src"].file_count == 2
    assert by_name["tests"].file_count == 1


def test_module_inventory_skips_dotfiles(tmp_repo: Path):
    _write(tmp_repo, ".git/config", "hidden")
    _write(tmp_repo, "src/app.py", "x=1")
    mods = _inventory_modules(tmp_repo)
    names = [m.name for m in mods]
    assert ".git" not in names
    assert "src" in names


def test_module_inventory_caps_at_20(tmp_repo: Path):
    for i in range(30):
        _write(tmp_repo, f"mod{i}/a.py", "x=1")
    mods = _inventory_modules(tmp_repo)
    assert len(mods) == 20


# ── Renderers ───────────────────────────────────────────────────────────


def _sample_report(name: str = "alpha") -> DocGenerationReport:
    return DocGenerationReport(
        app_name=name,
        app_path=f"/tmp/{name}",
        generated_at="2026-04-10T20:00:00+00:00",
        stack_scores={"python": 10, "docker": 9},
        primary_stack=["python", "docker"],
        entry_points=[EntryPoint("main.py", "python", "python main.py")],
        endpoints=[DetectedEndpoint("GET", "/health", "app/main.py", 5, "fastapi")],
        integrations=[
            DetectedIntegration("ftp", "ftp://partner.example.com", "src/x.py", 1, "FTP endpoint")
        ],
        modules=[
            ModuleEntry("src", "src", 10, {".py": 10}),
            ModuleEntry("tests", "tests", 5, {".py": 5}),
        ],
    )


def test_render_readme_includes_stack_and_entry_points():
    md = _render_readme(_sample_report())
    assert "# alpha" in md
    assert "python" in md
    assert "main.py" in md
    assert "python main.py" in md
    assert "src" in md  # module listed


def test_render_readme_with_empty_data():
    report = DocGenerationReport(
        app_name="beta", app_path="/tmp/beta", generated_at="2026-04-10T00:00:00+00:00"
    )
    md = _render_readme(report)
    assert "# beta" in md
    assert "could not be inferred" in md
    assert "No canonical entry point detected" in md


def test_render_architecture_has_mermaid_diagrams():
    md = _render_architecture(_sample_report())
    assert "```mermaid" in md
    assert "flowchart" in md
    assert "## C4: Context diagram" in md
    assert "## C4: Container diagram" in md
    assert "## C4: Component diagram" in md


def test_render_architecture_component_diagram_from_endpoints():
    md = _render_architecture(_sample_report())
    # Component diagram should reference the endpoint
    assert "GET /health" in md


def test_render_adr_has_baseline_counts():
    md = _render_adr(_sample_report())
    assert "ADR-0001" in md
    assert "alpha" in md
    assert "Entry points detected**: 1" in md
    assert "HTTP endpoints detected**: 1" in md
    assert "External integrations detected**: 1" in md


def test_render_runbook_lists_entry_point_run_command():
    md = _render_runbook(_sample_report())
    assert "python main.py" in md
    assert "Runbook" in md
    assert "Rollback" in md
    assert "Observability" in md


def test_render_runbook_empty_integrations_says_none():
    report = DocGenerationReport(
        app_name="gamma",
        app_path="/tmp/gamma",
        generated_at="2026-04-10T00:00:00+00:00",
    )
    md = _render_runbook(report)
    assert "No external integrations detected" in md


def test_render_api_with_endpoints():
    md = _render_api(_sample_report())
    assert "Total endpoints:** 1" in md
    assert "`GET`" in md
    assert "`/health`" in md


def test_render_api_empty_states_batch_only():
    report = DocGenerationReport(
        app_name="worker",
        app_path="/tmp/worker",
        generated_at="2026-04-10T00:00:00+00:00",
    )
    md = _render_api(report)
    assert "No HTTP endpoints detected" in md


def test_render_integrations_groups_by_type():
    report = _sample_report()
    report.integrations.append(
        DetectedIntegration("http", "https://api.x.com", "a.py", 10, "HTTP endpoint")
    )
    md = _render_integrations(report)
    assert "## ftp" in md
    assert "## http" in md


def test_render_integrations_empty_states_self_contained():
    report = DocGenerationReport(
        app_name="delta",
        app_path="/tmp/delta",
        generated_at="2026-04-10T00:00:00+00:00",
    )
    md = _render_integrations(report)
    assert "No external integrations detected" in md


# ── generate_docs end-to-end ────────────────────────────────────────────


def test_generate_docs_raises_on_missing_path():
    with pytest.raises(FileNotFoundError):
        generate_docs(app_name="x", app_path="/nonexistent/path/123456")


def test_generate_docs_produces_all_six_files(tmp_repo: Path):
    _write(tmp_repo, "main.py", "print('hello')")
    _write(tmp_repo, "requirements.txt", "fastapi\n")

    report = generate_docs(app_name="alpha", app_path=str(tmp_repo))
    assert set(report.files.keys()) == {
        "README.md",
        "ARCHITECTURE.md",
        "ADR-0001-initial-architecture.md",
        "RUNBOOK.md",
        "API.md",
        "INTEGRATIONS.md",
    }
    for content in report.files.values():
        assert content  # non-empty


def test_generate_docs_populates_report_fields(tmp_repo: Path):
    _write(tmp_repo, "main.py", "")
    _write(tmp_repo, "requirements.txt", "fastapi\n")
    _write(tmp_repo, "app/views.py", '@app.get("/health")\ndef h(): pass')

    report = generate_docs(app_name="alpha", app_path=str(tmp_repo))
    assert report.app_name == "alpha"
    assert report.generated_at
    assert report.primary_stack  # at least python detected
    assert report.entry_points  # main.py detected
    assert any(e.path == "/health" for e in report.endpoints)


def test_generate_docs_to_dict_is_json_serializable(tmp_repo: Path):
    _write(tmp_repo, "main.py", "")
    report = generate_docs(app_name="alpha", app_path=str(tmp_repo))
    d = report.to_dict()
    # Key fields
    assert "app_name" in d
    assert "primary_stack" in d
    assert "total_endpoints" in d
    assert "total_integrations" in d
    assert "files" in d
    # Round-trip JSON
    assert json.loads(json.dumps(d)) == d


def test_generate_docs_write_to_disk(tmp_repo: Path):
    _write(tmp_repo, "main.py", "")
    out = tmp_repo / "docs_out"

    report = generate_docs(
        app_name="alpha",
        app_path=str(tmp_repo),
        write_to_disk=True,
        output_dir=str(out),
    )
    assert out.exists()
    # All 6 files should be on disk
    for filename in report.files.keys():
        assert (out / filename).exists()
    assert len(report.written_to_disk) == 6
    assert not report.warnings


def test_generate_docs_write_to_disk_refuses_overwrite(tmp_repo: Path):
    _write(tmp_repo, "main.py", "")
    out = tmp_repo / "docs_out"
    out.mkdir()
    # Pre-existing file
    (out / "README.md").write_text("pre-existing", encoding="utf-8")

    report = generate_docs(
        app_name="alpha",
        app_path=str(tmp_repo),
        write_to_disk=True,
        output_dir=str(out),
        overwrite=False,
    )
    # Pre-existing should NOT be overwritten
    assert (out / "README.md").read_text(encoding="utf-8") == "pre-existing"
    assert any("Refused to overwrite" in w for w in report.warnings)
    # Other files (that did not exist) should still be written
    assert (out / "ARCHITECTURE.md").exists()


def test_generate_docs_write_to_disk_overwrite_true(tmp_repo: Path):
    _write(tmp_repo, "main.py", "")
    out = tmp_repo / "docs_out"
    out.mkdir()
    (out / "README.md").write_text("pre-existing", encoding="utf-8")

    report = generate_docs(
        app_name="alpha",
        app_path=str(tmp_repo),
        write_to_disk=True,
        output_dir=str(out),
        overwrite=True,
    )
    # Pre-existing should have been replaced
    assert (out / "README.md").read_text(encoding="utf-8") != "pre-existing"
    assert not any("Refused" in w for w in report.warnings)
