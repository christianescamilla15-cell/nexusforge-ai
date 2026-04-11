"""Agent Skills loader — Phase 5a (infrastructure).

Loads ``SKILL.md`` files from ``backend/skills/<skill_name>/SKILL.md``
and returns their frontmatter + body as a ``Skill`` dataclass.

Design constraints
------------------
1. **No PyYAML dependency.** The Agent Skills spec requires only two
   frontmatter fields (``name``, ``description``), both string-valued.
   A naive line parser is sufficient and keeps the requirements.txt
   footprint at zero.

2. **Backward compatibility.** This module is pure infrastructure —
   no agent code is rewired in Phase 5a. Existing calls to
   ``BaseAgent._build_system_prompt`` are untouched. The new
   ``_build_system_prompt_v2`` in ``base.py`` is an opt-in path that
   subclasses can call in a future migration PR (Phase 5b).

3. **Path safety.** Skill names are validated before being joined
   with the base directory. Any name containing ``..``, ``/``, or
   ``\\`` is refused. After joining, the resolved path is re-checked
   to still live under the base directory (defense-in-depth against
   symlink escape).

4. **Lazy cache.** Loading is memoized per-``SkillLoader`` instance
   so repeated agent invocations do not re-read disk. A singleton
   via ``get_default_loader()`` is provided for the hot path.

5. **Graceful degradation.** Any read or parse error returns ``None``
   rather than raising, so a malformed skill can never break an
   agent that happens to have a skill file of the same name.

Phase 5a scope
--------------
Ships:
- This loader module.
- ``BaseAgent._build_system_prompt_v2`` in ``base.py`` that routes
  through the loader with a fallback to the legacy method.
- ``GET /api/agents/skills`` endpoint in ``routes/agents.py``.

Does NOT ship:
- Migration of any agent's hardcoded prompt to SKILL.md form
  (that is Phase 5b — "Skills migration", L effort).
- Automatic skill selection when Claude is the provider (the
  Anthropic SDK has a separate `container` flag for real Agent
  Skills; for Ollama + Haiku + Groq, the body is injected as a
  plain system prompt, which is all Phase 5a needs).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# Path resolution: this file is at ``backend/app/agents/skill_loader.py``.
# parents[0] = agents, [1] = app, [2] = backend. So ``backend/skills``
# is ``parents[2] / "skills"``.
_DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"


@dataclass(frozen=True)
class Skill:
    """An in-memory representation of a parsed ``SKILL.md`` file."""

    name: str
    description: str
    body: str
    path: Path

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "body_length": len(self.body),
            # Path relative to repo root for display — fall back to
            # an absolute string if the relativize fails (e.g. in
            # tests with a synthetic base_dir).
            "path": self._display_path(),
        }

    def _display_path(self) -> str:
        try:
            # ``backend/skills/<skill>/SKILL.md`` — relative to the
            # backend directory (parents[2] from self.path, since the
            # layout is skills/<name>/SKILL.md).
            return str(self.path.relative_to(self.path.parents[2]))
        except (ValueError, IndexError):
            return str(self.path)


class SkillLoader:
    """Loads and caches SKILL.md files from a base skills directory."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir: Path = Path(base_dir) if base_dir else _DEFAULT_SKILLS_DIR
        self._cache: dict[str, Skill | None] = {}

    def load(self, skill_name: str) -> Skill | None:
        """Load a skill by its directory name. Returns ``None`` if the
        skill does not exist or fails to parse. Results are cached."""
        if skill_name in self._cache:
            return self._cache[skill_name]
        skill = self._load_uncached(skill_name)
        self._cache[skill_name] = skill
        return skill

    def list_skills(self) -> list[Skill]:
        """Return all valid skills in the base directory, sorted by
        directory name. Used by ``GET /api/agents/skills``.
        """
        if not self.base_dir.exists() or not self.base_dir.is_dir():
            return []
        result: list[Skill] = []
        try:
            entries = sorted(self.base_dir.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            logger.warning("Failed to iterate skills dir %s: %s", self.base_dir, exc)
            return []
        for entry in entries:
            if not entry.is_dir():
                continue
            skill = self.load(entry.name)
            if skill is not None:
                result.append(skill)
        return result

    def invalidate(self, skill_name: str | None = None) -> None:
        """Drop cached entries. Pass a name to evict one skill, or no
        argument to clear the entire cache. Primarily for tests."""
        if skill_name is None:
            self._cache.clear()
        else:
            self._cache.pop(skill_name, None)

    # ── Internal helpers ───────────────────────────────────────────────

    def _load_uncached(self, skill_name: str) -> Skill | None:
        if not self._is_safe_name(skill_name):
            logger.debug("Rejected unsafe skill name: %r", skill_name)
            return None

        skill_path = self.base_dir / skill_name / "SKILL.md"

        # Defense-in-depth: re-check that the resolved path is still
        # under the base directory. Guards against symlink escape
        # even though _is_safe_name already rejects obvious traversal.
        try:
            resolved = skill_path.resolve()
            base_resolved = self.base_dir.resolve()
            resolved.relative_to(base_resolved)
        except (OSError, ValueError):
            logger.debug("Skill path escapes base dir: %s", skill_path)
            return None

        if not skill_path.is_file():
            return None

        try:
            text = skill_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read skill %s: %s", skill_path, exc)
            return None

        parsed = self._parse(text)
        if parsed is None:
            logger.warning("Invalid SKILL.md frontmatter at %s", skill_path)
            return None

        meta, body = parsed
        return Skill(
            name=meta.get("name", skill_name),
            description=meta.get("description", ""),
            body=body,
            path=skill_path,
        )

    @staticmethod
    def _is_safe_name(skill_name: str) -> bool:
        if not skill_name:
            return False
        bad = ("/", "\\", "..", "\x00")
        return not any(b in skill_name for b in bad)

    @staticmethod
    def _parse(text: str) -> tuple[dict[str, str], str] | None:
        """Parse minimal YAML frontmatter.

        Expected shape::

            ---
            name: <value>
            description: <value>
            ---
            <body>

        Returns ``None`` if the frontmatter is missing, unterminated,
        or does not yield at least one of ``name`` / ``description``.
        """
        # Strip BOM + leading whitespace before the opening ``---``
        cleaned = text.lstrip("\ufeff").lstrip()
        if not cleaned.startswith("---"):
            return None

        lines = cleaned.splitlines()
        if not lines or lines[0].strip() != "---":
            return None

        # Find closing ``---``
        closing_idx: int | None = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break
        if closing_idx is None:
            return None

        meta: dict[str, str] = {}
        for raw in lines[1:closing_idx]:
            line = raw.rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Strip matched surrounding quotes if present
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key:
                meta[key] = value

        if "name" not in meta and "description" not in meta:
            return None

        body = "\n".join(lines[closing_idx + 1:]).strip()
        return meta, body


# ── Singleton ────────────────────────────────────────────────────────

_default_loader: SkillLoader | None = None


def get_default_loader() -> SkillLoader:
    """Return the process-wide default ``SkillLoader``, creating it on
    first call. Uses the default skills directory
    (``backend/skills``) which is the repo-local, not-user-writable
    location where skill files live."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SkillLoader()
    return _default_loader


def reset_default_loader() -> None:
    """Drop the singleton. Primarily for tests that need a fresh
    loader instance with a different ``base_dir``."""
    global _default_loader
    _default_loader = None
