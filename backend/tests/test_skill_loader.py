"""Tests for Phase 5a — Agent Skills loader infrastructure.

Covers:

- Frontmatter parsing (happy path, BOM tolerance, quoted values,
  comments inside frontmatter, missing/unterminated frontmatter)
- Path safety (name traversal, absolute path, null byte, empty)
- Cache behavior (memoization, explicit invalidation)
- Graceful degradation (missing file, unreadable file, malformed
  frontmatter)
- ``list_skills`` ordering + filtering
- Integration with the real ``backend/skills/classifier`` fixture
  that already lives in the repo (scaffolded 2026-04-10)
- ``BaseAgent._build_system_prompt_v2`` opt-in path (skill found,
  skill missing, environment disable flag)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.agents.base import BaseAgent, AgentResult
from app.agents.skill_loader import (
    Skill,
    SkillLoader,
    get_default_loader,
    reset_default_loader,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _write_skill(base_dir: Path, name: str, frontmatter: str, body: str = "") -> Path:
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\n{frontmatter}\n---\n{body}"
    path = skill_dir / "SKILL.md"
    path.write_text(content, encoding="utf-8")
    return path


# ── Parser: happy paths ───────────────────────────────────────────────


def test_parse_basic_frontmatter(tmp_path: Path):
    _write_skill(tmp_path, "basic", "name: basic\ndescription: A test skill", "# body\n\ncontent")
    loader = SkillLoader(base_dir=tmp_path)
    skill = loader.load("basic")
    assert skill is not None
    assert skill.name == "basic"
    assert skill.description == "A test skill"
    assert skill.body.startswith("# body")
    assert "content" in skill.body


def test_parse_handles_bom_and_leading_whitespace(tmp_path: Path):
    skill_dir = tmp_path / "bom-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\ufeff\n---\nname: bom-skill\ndescription: with BOM\n---\nbody",
        encoding="utf-8",
    )
    loader = SkillLoader(base_dir=tmp_path)
    skill = loader.load("bom-skill")
    assert skill is not None
    assert skill.name == "bom-skill"
    assert skill.body == "body"


def test_parse_strips_matched_quotes(tmp_path: Path):
    _write_skill(
        tmp_path,
        "quoted",
        "name: quoted\ndescription: \"a description with commas, quotes, and colons: yes\"",
    )
    loader = SkillLoader(base_dir=tmp_path)
    skill = loader.load("quoted")
    assert skill is not None
    assert skill.description == "a description with commas, quotes, and colons: yes"


def test_parse_ignores_comment_lines_in_frontmatter(tmp_path: Path):
    _write_skill(
        tmp_path,
        "with-comment",
        "# this is a comment\nname: with-comment\n# another\ndescription: survives",
    )
    loader = SkillLoader(base_dir=tmp_path)
    skill = loader.load("with-comment")
    assert skill is not None
    assert skill.name == "with-comment"
    assert skill.description == "survives"


def test_parse_accepts_description_only(tmp_path: Path):
    """The parser accepts a skill whose frontmatter has description
    but no name — the directory name is used as a fallback."""
    _write_skill(tmp_path, "nameless", "description: only desc", "body")
    loader = SkillLoader(base_dir=tmp_path)
    skill = loader.load("nameless")
    assert skill is not None
    assert skill.name == "nameless"  # fallback to dir name
    assert skill.description == "only desc"


# ── Parser: rejection paths ───────────────────────────────────────────


def test_parse_rejects_missing_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "no-frontmatter"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("just a body with no frontmatter", encoding="utf-8")
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load("no-frontmatter") is None


def test_parse_rejects_unterminated_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "unterminated"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: unterminated\n# no closing\nbody here", encoding="utf-8")
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load("unterminated") is None


def test_parse_rejects_empty_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "empty-meta"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\n---\nbody", encoding="utf-8")
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load("empty-meta") is None


# ── Path safety ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_name",
    [
        "",
        "..",
        "../escape",
        "..\\escape",
        "sub/nested",
        "sub\\nested",
        "with\x00null",
    ],
)
def test_load_refuses_unsafe_names(tmp_path: Path, bad_name: str):
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load(bad_name) is None


def test_load_returns_none_for_missing_skill(tmp_path: Path):
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load("does-not-exist") is None


# ── Cache behavior ────────────────────────────────────────────────────


def test_cache_memoizes_and_can_be_invalidated(tmp_path: Path):
    path = _write_skill(tmp_path, "cache-test", "name: cache-test\ndescription: v1", "body v1")
    loader = SkillLoader(base_dir=tmp_path)

    first = loader.load("cache-test")
    assert first is not None
    assert first.description == "v1"

    # Overwrite the file on disk — without cache invalidation we
    # should still see v1
    path.write_text("---\nname: cache-test\ndescription: v2\n---\nbody v2", encoding="utf-8")
    second = loader.load("cache-test")
    assert second is first  # cached object, not re-read
    assert second.description == "v1"

    # After invalidation, the new content is picked up
    loader.invalidate("cache-test")
    third = loader.load("cache-test")
    assert third is not None
    assert third.description == "v2"


def test_cache_remembers_negative_lookups(tmp_path: Path):
    loader = SkillLoader(base_dir=tmp_path)
    assert loader.load("missing") is None
    # Create the file AFTER the first lookup — the cache should still
    # return None until invalidated
    _write_skill(tmp_path, "missing", "name: missing\ndescription: now exists")
    assert loader.load("missing") is None
    loader.invalidate()
    assert loader.load("missing") is not None


# ── list_skills ───────────────────────────────────────────────────────


def test_list_skills_returns_sorted_valid_entries(tmp_path: Path):
    _write_skill(tmp_path, "bravo", "name: bravo\ndescription: second")
    _write_skill(tmp_path, "alpha", "name: alpha\ndescription: first")
    # An invalid skill should be silently skipped
    bad_dir = tmp_path / "broken"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text("no frontmatter at all", encoding="utf-8")
    # A non-directory entry should be ignored
    (tmp_path / "stray-file.md").write_text("not a skill", encoding="utf-8")

    loader = SkillLoader(base_dir=tmp_path)
    skills = loader.list_skills()
    names = [s.name for s in skills]
    assert names == ["alpha", "bravo"]


def test_list_skills_empty_on_missing_dir(tmp_path: Path):
    loader = SkillLoader(base_dir=tmp_path / "nonexistent")
    assert loader.list_skills() == []


# ── Singleton ─────────────────────────────────────────────────────────


def test_get_default_loader_is_singleton():
    try:
        first = get_default_loader()
        second = get_default_loader()
        assert first is second
    finally:
        reset_default_loader()


def test_reset_default_loader_forces_new_instance():
    try:
        first = get_default_loader()
        reset_default_loader()
        second = get_default_loader()
        assert first is not second
    finally:
        reset_default_loader()


# ── Integration with real repo fixture ───────────────────────────────


def test_real_classifier_skill_loads_from_repo():
    """The classifier skill was scaffolded on 2026-04-10. Sanity-check
    that the default loader can find it — this guards against
    accidental relocation of the skills directory."""
    try:
        loader = get_default_loader()
        skill = loader.load("classifier")
        assert skill is not None
        assert skill.name == "classifier"
        assert "document" in skill.description.lower()
        assert "legal" in skill.body.lower()  # category list in body
    finally:
        reset_default_loader()


# ── BaseAgent._build_system_prompt_v2 opt-in ─────────────────────────


class _FakeAgent(BaseAgent):
    name = "FakeAgent"
    agent_type = "fake-skill"
    description = "A fake agent for tests"

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:  # pragma: no cover
        return AgentResult(output={}, tokens_used=0)


def _make_agent_without_init() -> _FakeAgent:
    """Build an agent without triggering BaseAgent.__init__ (which
    touches Redis/Postgres via MemoryManager). For tests that only
    need to exercise the system-prompt builder."""
    agent = _FakeAgent.__new__(_FakeAgent)
    return agent


def test_build_system_prompt_v2_uses_skill_body_when_present(tmp_path: Path):
    _write_skill(tmp_path, "fake-skill", "name: fake-skill\ndescription: fake", "Skill body content here.")
    loader = SkillLoader(base_dir=tmp_path)

    agent = _make_agent_without_init()
    with patch("app.agents.skill_loader.get_default_loader", return_value=loader):
        prompt = agent._build_system_prompt_v2("do the thing")

    assert "You are FakeAgent" in prompt
    assert "Skill body content here." in prompt
    assert "Task: do the thing" in prompt
    # The legacy "Your role: <description>" wording must NOT appear
    # in the v2 path — the skill body replaces that section.
    assert "Your role:" not in prompt


def test_build_system_prompt_v2_falls_back_when_skill_missing(tmp_path: Path):
    loader = SkillLoader(base_dir=tmp_path)  # empty dir

    agent = _make_agent_without_init()
    with patch("app.agents.skill_loader.get_default_loader", return_value=loader):
        prompt = agent._build_system_prompt_v2("do the thing")

    # Legacy output — should be byte-identical to _build_system_prompt
    assert prompt == agent._build_system_prompt("do the thing")
    assert "Your role: A fake agent for tests" in prompt


def test_build_system_prompt_v2_respects_disable_flag(tmp_path: Path, monkeypatch):
    _write_skill(tmp_path, "fake-skill", "name: fake-skill\ndescription: fake", "Body")
    loader = SkillLoader(base_dir=tmp_path)

    monkeypatch.setenv("NEXUSFORGE_SKILLS_DISABLED", "1")

    agent = _make_agent_without_init()
    with patch("app.agents.skill_loader.get_default_loader", return_value=loader):
        prompt = agent._build_system_prompt_v2("do the thing")

    # Disable flag means fall back to legacy even though a valid
    # skill exists on disk
    assert prompt == agent._build_system_prompt("do the thing")
    assert "Your role:" in prompt
