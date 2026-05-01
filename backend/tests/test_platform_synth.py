"""Tests for the Platform Synthesizer (2026-05-01).

Three things to pin:
  1. Templates registry shape — at least one registered, ranking
     against a spec returns sane scores.
  2. Synthesizer — given a valid spec, writes the expected file
     tree to a temp dir; rejects path-traversal / non-empty target.
  3. Chat parser — handles the three LLM-output failure modes
     (pure JSON / fenced JSON / JSON + prose) without crashing.

The chat orchestrator's HTTP route is exercised separately via a
TestClient smoke test that ensures auth gating works (401 without
Bearer token).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform_synth.chat import _extract_json, _merge_spec
from app.platform_synth.schemas import (
    BuildRequest,
    PlatformSpec,
)
from app.platform_synth.synthesizer import synthesize
from app.platform_synth.templates import (
    list_templates,
    rank_for_spec,
)


# ─── templates registry ─────────────────────────────────────────────


def test_registry_has_all_four_templates():
    """All four templates ship in the registry."""
    ids = {t.template_id for t in list_templates()}
    assert ids == {
        "fastapi_react_postgres",
        "express_next_postgres",
        "django_postgres",
        "go_gin_postgres",
    }


def test_rank_floors_compatible_templates_at_ten_percent():
    """Empty/blank spec → every compatible template floors at 0.10
    so the UI never renders a row of zero-score (which looks broken)."""
    matches = rank_for_spec(PlatformSpec(description="building something"))
    for m in matches:
        # All templates compatible with no language picked → all
        # at least 0.10.
        assert m.score >= 0.10, f"{m.template.template_id} below floor"


def test_rank_excludes_template_when_language_mismatch():
    """If the user explicitly picks Go, the Python-only template
    must score 0 (so the frontend can hide it or show as
    incompatible)."""
    spec = PlatformSpec(language="go", description="api server")
    matches = rank_for_spec(spec)
    fastapi_match = next(
        m for m in matches if m.template.template_id == "fastapi_react_postgres"
    )
    assert fastapi_match.score == 0.0
    assert any("language mismatch" in s for s in fastapi_match.matched_signals)


def test_rank_boosts_when_stack_aligns():
    """A spec naming Python + FastAPI + React + Postgres should
    score the matching template much higher than a bare spec."""
    aligned = PlatformSpec(
        language="python",
        backend_framework="fastapi",
        frontend_framework="react",
        database="postgres",
        description="dashboard for inventory",
        features=["dashboard"],
    )
    matches = rank_for_spec(aligned)
    fastapi_match = next(
        m for m in matches if m.template.template_id == "fastapi_react_postgres"
    )
    # 0.30 (backend) + 0.20 (frontend) + 0.15 (db) + 0.10 (dashboard) = 0.75
    assert fastapi_match.score >= 0.70
    assert any("backend framework" in s for s in fastapi_match.matched_signals)


# ─── synthesizer ────────────────────────────────────────────────────


# ─── new templates (express+next, django, go+gin) ───────────────────


def test_express_next_template_matches_typescript_spec():
    """A typescript+express+next+postgres spec should rank
    express_next_postgres significantly above fastapi_react_postgres
    (which scores 0 due to language mismatch)."""
    spec = PlatformSpec(
        language="typescript",
        backend_framework="express",
        frontend_framework="next",
        database="postgres",
        description="ecommerce site with ssr",
    )
    matches = {m.template.template_id: m for m in rank_for_spec(spec)}
    assert matches["express_next_postgres"].score >= 0.70
    # FastAPI rejects: language mismatch.
    assert matches["fastapi_react_postgres"].score == 0.0


def test_django_template_matches_admin_use_case():
    """A spec naming Python + Django should rank django above
    fastapi when 'admin' or 'internal tool' is in features."""
    spec = PlatformSpec(
        language="python",
        backend_framework="django",
        database="postgres",
        description="internal tool for the back office",
        features=["admin"],
    )
    matches = {m.template.template_id: m for m in rank_for_spec(spec)}
    # Django: 0.30 (backend) + 0.15 (db) + 0.10 (admin) + 0.10 (internal tool) = 0.65
    # FastAPI: no backend match = 0.10 floor + 0.10 (internal tool) = 0.20
    assert matches["django_postgres"].score > matches["fastapi_react_postgres"].score


def test_go_gin_template_matches_microservice():
    """Go + Gin spec should pick go_gin_postgres."""
    spec = PlatformSpec(
        language="go",
        backend_framework="gin",
        database="postgres",
        description="high throughput microservice api",
    )
    matches = {m.template.template_id: m for m in rank_for_spec(spec)}
    assert matches["go_gin_postgres"].score >= 0.55
    # Python templates can't fit Go.
    assert matches["fastapi_react_postgres"].score == 0.0
    assert matches["django_postgres"].score == 0.0


def test_render_express_next_emits_typescript_files(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    target = tmp_path / "express-app"
    spec = PlatformSpec(
        project_name="express-app",
        language="typescript",
        backend_framework="express",
        frontend_framework="next",
        database="postgres",
    )
    req = BuildRequest(
        template_id="express_next_postgres",
        spec=spec,
        target_dir=str(target),
    )
    result = synthesize(req)
    assert result.status == "complete"
    assert (target / "backend" / "src" / "index.ts").is_file()
    assert (target / "backend" / "tsconfig.json").is_file()
    assert (target / "frontend" / "app" / "page.tsx").is_file()
    assert (target / "frontend" / "next.config.js").is_file()
    assert "express-app" in (target / "README.md").read_text(encoding="utf-8")


def test_render_django_emits_settings_with_correct_module(tmp_path, monkeypatch):
    """The Django settings.py must reference the project module
    name (sanitized to a valid Python identifier)."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    target = tmp_path / "my-django-app"
    spec = PlatformSpec(
        project_name="my-django-app",
        language="python",
        backend_framework="django",
        database="postgres",
    )
    req = BuildRequest(
        template_id="django_postgres",
        spec=spec,
        target_dir=str(target),
    )
    result = synthesize(req)
    assert result.status == "complete"
    # Hyphen in project_name must be converted to underscore for
    # the Python module dir.
    py_module = "my_django_app"
    assert (target / py_module / "settings.py").is_file()
    assert (target / py_module / "urls.py").is_file()
    assert (target / py_module / "wsgi.py").is_file()
    assert (target / "core" / "models.py").is_file()
    assert (target / "core" / "admin.py").is_file()
    assert (target / "manage.py").is_file()
    settings = (target / py_module / "settings.py").read_text(encoding="utf-8")
    # ROOT_URLCONF must point to the sanitized module name.
    assert f'ROOT_URLCONF = "{py_module}.urls"' in settings


def test_render_go_emits_go_module_with_project_name(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    target = tmp_path / "go-microservice"
    spec = PlatformSpec(
        project_name="go-microservice",
        language="go",
        backend_framework="gin",
        database="postgres",
    )
    req = BuildRequest(
        template_id="go_gin_postgres",
        spec=spec,
        target_dir=str(target),
    )
    result = synthesize(req)
    assert result.status == "complete"
    assert (target / "main.go").is_file()
    assert (target / "items.go").is_file()
    assert (target / "db.go").is_file()
    assert (target / "go.mod").is_file()
    assert (target / "migrations" / "001_init.sql").is_file()
    # go.mod's `module` directive must use the project name.
    gomod = (target / "go.mod").read_text(encoding="utf-8")
    assert "module go-microservice" in gomod


# ─── synthesizer ────────────────────────────────────────────────────


def test_synthesize_writes_expected_files(tmp_path, monkeypatch):
    """Given a minimal valid spec, the synthesizer writes a
    real, navigable project tree."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))

    target = tmp_path / "my-test-project"
    spec = PlatformSpec(
        project_name="my-test-project",
        description="Test project for synthesizer",
        language="python",
        backend_framework="fastapi",
        frontend_framework="react",
        database="postgres",
    )
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
    )
    result = synthesize(req)

    assert result.status == "complete"
    assert result.files_written > 5  # README + several backend + frontend files
    # Spot-check the canonical files exist.
    assert (target / "README.md").is_file()
    assert (target / "backend" / "app" / "main.py").is_file()
    assert (target / "frontend" / "package.json").is_file()
    assert (target / "frontend" / "src" / "App.jsx").is_file()
    assert (target / "backend" / "app" / "db" / "migrations" / "001_init.sql").is_file()

    # Project name was substituted into README.
    readme = (target / "README.md").read_text(encoding="utf-8")
    assert "my-test-project" in readme


def test_synthesize_refuses_target_outside_root(tmp_path, monkeypatch):
    """Path traversal / paths outside the synth root must be
    rejected. This is the primary security guard."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))

    spec = PlatformSpec(project_name="evil-project")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir="/tmp/escape",  # NOT under tmp_path
    )
    with pytest.raises(ValueError, match="must be under"):
        synthesize(req)


def test_synthesize_refuses_non_empty_target(tmp_path, monkeypatch):
    """If target_dir already exists with content, refuse to
    overwrite — protects against clobbering an existing project."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))

    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("don't clobber me")

    spec = PlatformSpec(project_name="occupied")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
    )
    with pytest.raises(ValueError, match="not empty"):
        synthesize(req)


def test_synthesize_requires_project_name(tmp_path, monkeypatch):
    """Template render fails fast if project_name slot is empty."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))

    target = tmp_path / "no-name"
    spec = PlatformSpec(description="no project name")  # missing project_name
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
    )
    with pytest.raises(ValueError, match="project_name is required"):
        synthesize(req)


# ─── chat parser ────────────────────────────────────────────────────


def test_extract_json_pure():
    raw = '{"assistant_message": "hi", "spec_updates": {"language": "python"}}'
    parsed = _extract_json(raw)
    assert parsed["spec_updates"]["language"] == "python"


def test_extract_json_fenced():
    raw = """Sure, here you go:
```json
{"assistant_message": "hi", "spec_updates": {"language": "go"}}
```
"""
    parsed = _extract_json(raw)
    assert parsed["spec_updates"]["language"] == "go"


def test_extract_json_prose_then_object():
    raw = (
        "I think you want a dashboard. "
        '{"assistant_message": "ok", "spec_updates": {"language": "rust"}} '
        "Hope that helps."
    )
    parsed = _extract_json(raw)
    assert parsed["spec_updates"]["language"] == "rust"


def test_extract_json_raises_when_no_object():
    with pytest.raises(ValueError):
        _extract_json("This is just prose, no JSON here.")


# ─── spec merge ─────────────────────────────────────────────────────


def test_merge_spec_overwrites_scalars_and_appends_lists():
    """Scalar fields overwrite; list fields (features/integrations)
    accumulate so the LLM doesn't lose previously-noted info."""
    current = PlatformSpec(
        project_name="old",
        language="python",
        features=["dashboard"],
        integrations=["slack"],
    )
    merged = _merge_spec(current, {
        "project_name": "new",
        "features": ["csv export"],
        "integrations": ["stripe"],
    })
    assert merged.project_name == "new"  # scalar overwrite
    assert merged.language == "python"  # untouched
    # Lists accumulate.
    assert "dashboard" in merged.features
    assert "csv export" in merged.features
    assert "slack" in merged.integrations
    assert "stripe" in merged.integrations


def test_merge_spec_ignores_unknown_keys():
    """LLM-invented slots don't pollute the spec."""
    merged = _merge_spec(None, {
        "project_name": "test",
        "magical_unicorn": "shiny",
    })
    assert merged.project_name == "test"
    assert not hasattr(merged, "magical_unicorn")


def test_merge_spec_preserves_on_invalid_value():
    """If LLM emits an invalid Literal value (e.g. language='erlang'),
    the previous valid spec is preserved (degraded but not crashed)."""
    current = PlatformSpec(language="python")
    merged = _merge_spec(current, {"language": "erlang"})  # not in our enum
    # Either the old python is preserved or the new erlang silently drops.
    assert merged.language == "python"


def test_merge_spec_explicit_null_keeps_current():
    """An explicit null in `spec_updates` means 'I don't know' —
    do NOT clobber the current value with None."""
    current = PlatformSpec(project_name="kept", language="python")
    merged = _merge_spec(current, {"project_name": None, "language": "go"})
    assert merged.project_name == "kept"
    assert merged.language == "go"


# ─── HTTP route smoke ───────────────────────────────────────────────


@pytest.fixture
def client():
    """Bare router on a fresh app — auth check is in-handler so
    we don't need the global middleware here."""
    from app.routes.platform_synth import router
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def test_chat_endpoint_requires_auth(client):
    resp = client.post("/platform-synth/chat", json={"user_message": "hi"})
    assert resp.status_code == 401


def test_templates_endpoint_requires_auth(client):
    resp = client.get("/platform-synth/templates")
    assert resp.status_code == 401


def test_build_endpoint_requires_auth(client):
    resp = client.post(
        "/platform-synth/build",
        json={"template_id": "x", "spec": {"project_name": "y"}, "target_dir": "/tmp"},
    )
    assert resp.status_code == 401
