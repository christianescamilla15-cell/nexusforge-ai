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

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform_synth.chat import _extract_json, _merge_spec
from app.platform_synth.schemas import (
    BuildRequest,
    PlatformSpec,
)
from app.platform_synth.synthesizer import synthesize as _synthesize_async
from app.platform_synth.templates import (
    list_templates,
    rank_for_spec,
)


def synthesize(req):
    """Sync wrapper around the now-async synthesize so tests don't
    need @pytest.mark.asyncio decorators on every case. Each call
    runs in its own event loop — fine for tests, would never do
    this in production code."""
    return asyncio.run(_synthesize_async(req))


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


# ─── post-build (git init / gh repo create) ────────────────────────


def test_post_build_sanitize_repo_name_accepts_normal():
    from app.platform_synth.post_build import _sanitize_repo_name
    assert _sanitize_repo_name("my-app") == "my-app"
    assert _sanitize_repo_name("project_name_123") == "project_name_123"


def test_post_build_sanitize_repo_name_rejects_path_traversal():
    """The repo name is passed to gh CLI. Even though we use args
    list (no shell), GitHub itself rejects these — fail fast on
    our end with a clear error rather than relying on gh."""
    from app.platform_synth.post_build import _sanitize_repo_name
    assert _sanitize_repo_name("..") is None
    assert _sanitize_repo_name("../etc/passwd") is None
    assert _sanitize_repo_name("a..b") is None
    assert _sanitize_repo_name(".hidden") is None
    assert _sanitize_repo_name("trailing.") is None
    assert _sanitize_repo_name("") is None
    assert _sanitize_repo_name("name with spaces") is None
    assert _sanitize_repo_name("name/slash") is None
    assert _sanitize_repo_name("a" * 101) is None  # too long


def test_post_build_init_git_repo_skips_when_git_missing(tmp_path, monkeypatch):
    """If `git` isn't on PATH, init_git_repo returns warnings and
    does NOT raise. Project on disk is unaffected."""
    monkeypatch.setattr("app.platform_synth.post_build.shutil.which", lambda _: None)
    ok, sha, warnings = __import__(
        "app.platform_synth.post_build", fromlist=["init_git_repo"]
    ).init_git_repo(tmp_path, "my-app")
    assert ok is False
    assert sha is None
    assert any("git binary not found" in w for w in warnings)


def test_post_build_init_git_repo_calls_correct_args(tmp_path, monkeypatch):
    """Confirm the args we pass to `git init` / `git commit` —
    pin the security-critical bits: --initial-branch=main,
    NEVER shell=True (we use args list)."""
    from app.platform_synth import post_build

    monkeypatch.setattr(post_build.shutil, "which", lambda name: f"/usr/bin/{name}")

    calls = []

    def fake_run(cmd, cwd, timeout=60):
        calls.append((cmd, str(cwd)))
        # Make every command "succeed" so the flow continues.
        if cmd[:3] == ["git", "rev-parse", "HEAD"]:
            return 0, "abc123def456" + "0" * 28 + "\n", ""
        return 0, "", ""

    monkeypatch.setattr(post_build, "_run", fake_run)

    ok, sha, warnings = post_build.init_git_repo(tmp_path, "my-app")
    assert ok is True
    assert sha and sha.startswith("abc123def456")
    assert warnings == []

    # First call must be `git init --initial-branch=main`.
    assert calls[0][0] == ["git", "init", "--initial-branch=main"]
    # Second `git add -A`.
    assert calls[1][0] == ["git", "add", "-A"]
    # Third call: commit. Must use args list, must include
    # synthesizer identity to avoid leaking host's git config,
    # must include project_name in commit message.
    commit_cmd = calls[2][0]
    assert commit_cmd[0] == "git"
    assert "commit" in commit_cmd
    assert "my-app" in " ".join(commit_cmd)


def test_post_build_create_github_repo_skips_when_gh_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.platform_synth.post_build.shutil.which", lambda _: None)
    from app.platform_synth.post_build import create_github_repo
    url, warnings = create_github_repo(tmp_path, "my-app", "private")
    assert url is None
    assert any("gh CLI not found" in w for w in warnings)


def test_post_build_create_github_repo_rejects_unsafe_name(tmp_path, monkeypatch):
    """Bad repo name → fail fast, NEVER call gh with garbage."""
    from app.platform_synth import post_build

    monkeypatch.setattr(post_build.shutil, "which", lambda _: "/usr/bin/gh")
    calls = []
    monkeypatch.setattr(
        post_build, "_run",
        lambda *a, **kw: (calls.append(a) or (0, "", "")) or (0, "", ""),
    )

    url, warnings = post_build.create_github_repo(tmp_path, "../escape", "private")
    assert url is None
    assert any("not safe for GitHub repo name" in w for w in warnings)
    # And critically: gh was NEVER invoked.
    assert calls == []


def test_post_build_create_github_repo_parses_url_from_stdout(tmp_path, monkeypatch):
    """When `gh repo create --push` succeeds, parse the URL it
    prints and surface it to the caller."""
    from app.platform_synth import post_build

    monkeypatch.setattr(post_build.shutil, "which", lambda _: "/usr/bin/gh")

    def fake_run(cmd, cwd, timeout=60):
        if cmd[:3] == ["gh", "auth", "status"]:
            return 0, "logged in", ""
        if cmd[:3] == ["gh", "repo", "create"]:
            return 0, "https://github.com/christianescamilla15-cell/my-app\n", ""
        return 0, "", ""

    monkeypatch.setattr(post_build, "_run", fake_run)

    url, warnings = post_build.create_github_repo(tmp_path, "my-app", "private")
    assert url == "https://github.com/christianescamilla15-cell/my-app"


def test_synthesize_skips_post_build_when_flags_off(tmp_path, monkeypatch):
    """With both flags False, the synthesizer never touches git/gh
    even if they're available on PATH."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import post_build

    init_called = []
    monkeypatch.setattr(
        post_build, "init_git_repo",
        lambda *a, **kw: init_called.append(a) or (False, None, []),
    )

    target = tmp_path / "no-git"
    spec = PlatformSpec(project_name="no-git")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        # both flags default False
    )
    result = synthesize(req)
    assert result.git_initialized is False
    assert result.github_repo_url is None
    assert init_called == []  # not called at all


def test_synthesize_runs_git_init_when_flag_on(tmp_path, monkeypatch):
    """With git_init=True, init_git_repo runs and the result
    surfaces git_initialized + sha."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import synthesizer as synth_mod

    monkeypatch.setattr(
        synth_mod, "init_git_repo",
        lambda target, name: (True, "deadbeef" * 5, []),
    )

    target = tmp_path / "with-git"
    spec = PlatformSpec(project_name="with-git")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        git_init=True,
    )
    result = synthesize(req)
    assert result.git_initialized is True
    assert result.git_first_commit_sha == "deadbeef" * 5


# ─── Mythos pre-flight ─────────────────────────────────────────────


def test_mythos_preflight_skipped_when_flag_off(tmp_path, monkeypatch):
    """Without mythos_preflight=True, scanner is NEVER invoked
    (saves 1-3s per build for the common path)."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import synthesizer as synth_mod

    called = []

    async def fake_preflight(target):
        called.append(target)
        return {
            "mythos_ran": True,
            "mythos_score": 100,
            "mythos_critical_count": 0,
            "mythos_high_count": 0,
            "mythos_findings_summary": [],
        }

    monkeypatch.setattr(synth_mod, "run_preflight", fake_preflight)

    target = tmp_path / "no-preflight"
    spec = PlatformSpec(project_name="no-preflight")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        # mythos_preflight defaults False
    )
    result = synthesize(req)
    assert result.mythos_ran is False
    assert called == []


def test_mythos_preflight_runs_and_surfaces_clean_score(tmp_path, monkeypatch):
    """Happy path: scanner runs, finds nothing, score=100, no
    findings in summary, status remains 'complete'."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import synthesizer as synth_mod

    async def fake_preflight(target):
        return {
            "mythos_ran": True,
            "mythos_score": 100,
            "mythos_critical_count": 0,
            "mythos_high_count": 0,
            "mythos_findings_summary": [],
        }

    monkeypatch.setattr(synth_mod, "run_preflight", fake_preflight)

    target = tmp_path / "clean-scan"
    spec = PlatformSpec(project_name="clean-scan")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        mythos_preflight=True,
    )
    result = synthesize(req)
    assert result.mythos_ran is True
    assert result.mythos_score == 100
    assert result.mythos_critical_count == 0
    assert result.status == "complete"


def test_mythos_preflight_with_critical_findings_marks_partial(tmp_path, monkeypatch):
    """If Mythos finds critical/high issues, build status drops
    to 'partial' and the findings appear in
    mythos_findings_summary + post_build_warnings."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import synthesizer as synth_mod

    async def fake_preflight(target):
        return {
            "mythos_ran": True,
            "mythos_score": 70,
            "mythos_critical_count": 2,
            "mythos_high_count": 1,
            "mythos_findings_summary": [
                "[critical] Hardcoded secret in backend/auth.py:15",
                "[critical] SQL injection in backend/items.py:42",
                "[high] Missing CSRF token on state-changing route",
            ],
        }

    monkeypatch.setattr(synth_mod, "run_preflight", fake_preflight)

    target = tmp_path / "scary-scan"
    spec = PlatformSpec(project_name="scary-scan")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        mythos_preflight=True,
    )
    result = synthesize(req)
    assert result.mythos_ran is True
    assert result.mythos_critical_count == 2
    assert result.mythos_high_count == 1
    assert result.mythos_score == 70
    assert len(result.mythos_findings_summary) == 3
    # Build still completes (files written), but status reflects warnings.
    assert result.status == "partial"
    # Warnings include both severity buckets.
    joined_warnings = " ".join(result.post_build_warnings)
    assert "2 CRITICAL" in joined_warnings
    assert "1 HIGH" in joined_warnings


def test_mythos_preflight_handles_scanner_failure_gracefully(tmp_path, monkeypatch):
    """Scanner import error / runtime crash → mythos_ran=False
    with a warning. Build still completes."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))
    from app.platform_synth import synthesizer as synth_mod

    async def broken_preflight(target):
        # Mimic mythos_preflight.run_preflight()'s graceful shape
        # when something explodes inside.
        return {
            "mythos_ran": False,
            "mythos_score": None,
            "mythos_critical_count": 0,
            "mythos_high_count": 0,
            "mythos_findings_summary": ["scan errored: ImportError: missing dep"],
        }

    monkeypatch.setattr(synth_mod, "run_preflight", broken_preflight)

    target = tmp_path / "broken-scan"
    spec = PlatformSpec(project_name="broken-scan")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        mythos_preflight=True,
    )
    # Must NOT raise. Build completes (status complete because no
    # high/critical counted), summary surfaces the error.
    result = synthesize(req)
    assert result.mythos_ran is False
    assert result.status == "complete"  # no critical/high → no warning bump
    assert any("scan errored" in s for s in result.mythos_findings_summary)


def test_synthesize_refuses_gh_create_without_git_init(tmp_path, monkeypatch):
    """github_repo_create=True + git_init=False → warning, not crash.
    GitHub repo creation requires a local repo to push."""
    monkeypatch.setenv("PLATFORM_SYNTH_ROOT", str(tmp_path))

    target = tmp_path / "gh-without-git"
    spec = PlatformSpec(project_name="gh-without-git")
    req = BuildRequest(
        template_id="fastapi_react_postgres",
        spec=spec,
        target_dir=str(target),
        git_init=False,
        github_repo_create=True,
    )
    result = synthesize(req)
    assert result.git_initialized is False
    assert result.github_repo_url is None
    assert any("git_init was False" in w for w in result.post_build_warnings)


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
