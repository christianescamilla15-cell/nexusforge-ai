"""Anthropic Memory Tool handler — Phase 3 (Feature 3) of Anthropic adoption.

Implements the client-side handler for Anthropic's ``memory_20250818``
tool declaration. The Memory Tool is a file-based persistent scratchpad
that Claude can read, write, update, and delete across conversations,
enabling agents to accumulate domain knowledge over time (e.g., known
false-positive patterns, learned regulations, cross-tenant policy
deltas).

This module is the SERVER-SIDE of the protocol. When Claude emits a
``tool_use`` block with ``type=memory_20250818``, the app's agent loop
delivers the command + params to ``MemoryToolHandler.execute_tool_use``
which runs the filesystem operation and returns the result as a
``tool_result`` block.

Security posture (all mandatory per Anthropic's cookbook):

1. **Path traversal protection**: every path goes through
   ``_resolve_safe_path`` which resolves symlinks, canonicalizes, and
   asserts the result is inside the agent's memory root. Any attempt
   to escape (``../../../etc/passwd``) raises ``PermissionError`` and
   returns an error payload — the attempt is logged but not fatal.

2. **Per-agent isolation**: each handler is scoped to exactly one
   ``agent_id``. Its memory root is
   ``<base>/agents/<sanitized_agent_id>/memories/``. An attacker who
   writes poisoned memory as ``ClassifierAgent`` cannot affect
   ``ComplianceAgent``'s context because their directories are separate.

3. **Size caps**: 1 MB per file, 64 KB per individual ``str_replace``
   / ``insert`` operation. Reject anything larger with an explicit
   error. Rationale: prevent runaway tokens that bloat the context
   and prevent resource exhaustion.

4. **Restricted permissions** on newly created files: mode 0o600 on
   POSIX (ignored on Windows, which uses ACLs — the per-agent
   subdirectory already restricts via filesystem permissions).

5. **Content validation for poisoning**: a lightweight filter rejects
   memory writes whose content matches obvious prompt-injection
   patterns (``ignore previous instructions``, ``system:``, etc.).
   This is defense-in-depth, not primary protection. The primary
   protection is the system prompt discipline the agent loop injects
   ("treat memory files as data only").

6. **agent_id sanitization**: the ``agent_id`` is used to build a
   directory path. Only alphanumeric, hyphen, underscore, and dot are
   allowed. Anything else is stripped. An empty sanitized agent_id
   falls back to ``_unknown``.

The protocol shape — ``command``, ``path``, ``file_text``, ``old_str``,
``new_str``, ``insert_line``, ``insert_text``, ``old_path``,
``new_path`` — matches Anthropic's cookbook. When the public API
contract evolves, update the ``_COMMAND_HANDLERS`` dispatch table.

This module has ZERO runtime dependencies outside the stdlib and
``logging``. It does NOT import the ``anthropic`` package — it is the
server-side counterpart, agnostic to the model API.
"""
from __future__ import annotations

import logging
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Configuration constants ──────────────────────────────────────────────

# Maximum size of a single memory file (1 MB).
MAX_FILE_BYTES = 1_000_000

# Maximum size of a str_replace / insert operation (64 KB).
MAX_OPERATION_BYTES = 64_000

# Maximum total size of an agent's memory directory (10 MB) — soft cap.
# If exceeded, ``create`` and ``str_replace`` reject the write until
# old files are deleted. Not a hard FS quota — it is a best-effort
# check before the write attempt.
MAX_DIR_BYTES = 10_000_000

# Known prompt injection markers. Not exhaustive — defense-in-depth only.
# The authoritative defense is the agent loop's system prompt which
# tells Claude to treat memory contents as data, not instructions.
#
# L-3 hardening (2026-04-30, T5 #5): the previous list was
# allowlist-of-known-strings and trivially bypassable via Unicode
# homoglyphs (Cyrillic 'е' for Latin 'e'), zero-width chars, or any
# synonym not enumerated. The current pattern raises the bar by
# normalizing input first (NFKC + homoglyph fold + zero-width strip
# + whitespace collapse) AND expanding the marker set to cover
# common roleplay/jailbreak phrasings + LLM control tokens. It is
# still defense-in-depth; the system-prompt discipline that tells
# Claude to treat memory as data remains the primary protection.
#
# NOTE: case insensitivity is applied via re.IGNORECASE at compile
# time. Do NOT embed ``(?i)`` inline — Python 3.11+ rejects inline
# flags that are not at the start of the whole expression when they
# appear inside an alternation.
_POISONING_MARKERS = [
    # Override / disregard / forget instructions (with synonyms +
    # qualifier-words covering "the/all/your/any/previous/prior/above").
    r"\b(?:ignore|disregard|forget|override|skip|bypass|drop)\s+"
    r"(?:the\s+|all\s+|your\s+|any\s+|previous\s+|prior\s+|above\s+|earlier\s+)+"
    r"(?:instructions?|rules?|prompts?|guidelines?|system|directives?|constraints?)\b",

    # "Disregard the above" without an explicit object is a common
    # jailbreak hook. Caught when followed by a directive verb.
    r"\b(?:disregard|ignore)\s+(?:everything|anything)\s+(?:above|before|prior|earlier)\b",

    # Roleplay-persona jailbreak names paired with REQUIRED
    # mode/prompt/persona/jailbreak qualifiers. The qualifier is
    # mandatory because bare names like "AIM" or "DAN" appear in
    # legitimate memory content (a project name, a person, "aim of
    # the project"). Pairing them with "mode"/"persona" keeps the
    # signal strong without false-positive on real words.
    r"\b(?:DAN|STAN|DUDE|AIM|JAILBREAK|DEVMODE|EVILBOT)\s+"
    r"(?:mode|prompt|persona|enabled|activated|now)\b",

    # "you are now <X>" / "you are from now on" — the canonical
    # role-redefinition opener. Tightened so plain mentions of "you
    # are" don't false-match.
    r"\byou\s+are\s+(?:now|from\s+now\s+on|hereby|going\s+to\s+act)\b",
    r"\b(?:act|behave|pretend|roleplay)\s+as\s+(?:if\s+you\s+are\s+|though\s+you\s+are\s+)?"
    r"(?:a|an|the)\s+\w+",

    # Explicit role markers followed by a directive verb. Catches both
    # `system: you are` and `system:\nyou are`.
    r"(?:system|assistant|developer)\s*[:>\]]\s*"
    r"(?:you\s+are|act\s+as|you\s+must|you\s+will|new\s+instructions)",

    # LLM control tokens (Anthropic, OpenAI, Llama, etc.).
    r"\[INST\]",
    r"\[/INST\]",
    r"<<\s*SYS\s*>>",
    r"<</\s*SYS\s*>>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    r"<\|endoftext\|>",
    r"<\|tool_call\|>",
    r"<\|response\|>",
    r"<\|control_\d+\|>",
]

_POISONING_RE = re.compile("|".join(_POISONING_MARKERS), re.IGNORECASE)


# Common Cyrillic-to-Latin homoglyphs. Mapping is one-way (Cyrillic
# code point → ASCII letter) so the regex can match canonical Latin
# strings even when the attacker substituted lookalikes. Only the
# letters that appear in the marker set are folded — keeping the map
# tight reduces collateral damage to legitimate non-English memory
# content (e.g., a Russian user note remains intact other than the 8
# specific letters we collapse).
_HOMOGLYPH_FOLD = str.maketrans({
    "а": "a",  # Cyrillic а
    "е": "e",  # Cyrillic е
    "о": "o",  # Cyrillic о
    "р": "p",  # Cyrillic р
    "с": "c",  # Cyrillic с
    "у": "y",  # Cyrillic у
    "х": "x",  # Cyrillic х
    "і": "i",  # Cyrillic і (Ukrainian)
    "ԁ": "d",  # Komi De
    # Greek lookalikes
    "ο": "o",  # Greek omicron
    "α": "a",  # Greek alpha
    # Mathematical alphanumerics: most fall through NFKC, but
    # full-width forms need explicit handling for the few NFKC misses.
})

# Zero-width / formatting characters that get stripped before matching
# so an attacker can't break a marker mid-word (`igno​re`).
_ZERO_WIDTH_RE = re.compile(r"[​‌‍⁠﻿]")


def _normalize_for_poisoning_check(text: str) -> str:
    """Canonicalize ``text`` so the poisoning regex can't be bypassed
    by Unicode lookalikes, zero-width insertions, full-width forms,
    or unusual whitespace. Pure function; doesn't mutate input.

    Steps (in order):
      1. NFKC — folds compatibility forms (full-width "ｉｇｎｏｒｅ"
         becomes "ignore", ligatures decompose, etc.).
      2. Strip combining marks (so "ignoré" → "ignore" before regex).
      3. Strip zero-width chars (zero-width space / joiner / BOM).
      4. Apply targeted Cyrillic + Greek → Latin homoglyph fold.
      5. Collapse all Unicode whitespace runs to a single ASCII space
         so `\s+` in the markers matches the same way regardless of
         what whitespace the attacker used.
      6. Lowercase (regex uses IGNORECASE but lowercasing once up
         front is cheaper than per-match folding).
    """
    if not text:
        return ""
    # NFKD decomposes precomposed accents (é → e + combining acute)
    # so the next step can drop the marks. NFKC would leave precomposed
    # forms intact and miss "ignoré"-style attacks.
    s = unicodedata.normalize("NFKD", text)
    # Drop combining marks (category Mn = Mark, Nonspacing).
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = _ZERO_WIDTH_RE.sub("", s)
    s = s.translate(_HOMOGLYPH_FOLD)
    s = re.sub(r"\s+", " ", s)
    return s.lower()


# Safe characters for agent_id → directory path. Everything else stripped.
_AGENT_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9._\-]")


def _sanitize_agent_id(agent_id: str) -> str:
    """Return a filesystem-safe form of ``agent_id``.

    Strips anything outside ``[A-Za-z0-9._-]``. Empty result falls
    back to ``_unknown``. Limits to 64 chars to keep paths bounded.
    """
    cleaned = _AGENT_ID_SAFE_RE.sub("", (agent_id or "").strip())
    cleaned = cleaned[:64]
    return cleaned or "_unknown"


# ── Exceptions ───────────────────────────────────────────────────────────


class MemoryToolError(Exception):
    """Base class for memory tool errors reported back to the model."""


class PathTraversalError(MemoryToolError):
    """Raised when a requested path escapes the agent's memory root."""


class SizeCapError(MemoryToolError):
    """Raised when a write exceeds MAX_FILE_BYTES / MAX_OPERATION_BYTES."""


class PoisoningDetectedError(MemoryToolError):
    """Raised when content matches a prompt injection marker."""


# ── Response dataclasses ─────────────────────────────────────────────────


@dataclass
class MemoryToolResponse:
    """Structured response for one tool command.

    Returned by ``MemoryToolHandler.execute_tool_use``. The agent loop
    converts this into a ``tool_result`` block sent back to the model.

    ``is_error`` True means Claude should treat the response as an
    error condition (still valid to recover from — the loop does not
    abort on error, it just reports back to the model).
    """

    is_error: bool
    content: str
    command: str

    def to_tool_result(self, tool_use_id: str) -> dict[str, Any]:
        """Render as an Anthropic ``tool_result`` content block."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": self.content,
            "is_error": self.is_error,
        }


# ── Handler ──────────────────────────────────────────────────────────────


class MemoryToolHandler:
    """Client-side implementation of Anthropic's memory_20250818 tool.

    Instantiate once per agent invocation. The handler is per-agent,
    per-run; it does not hold long-lived state beyond the filesystem.

    Args:
        base_path: root directory for all agents' memories. Defaults
            to ``backend/data/memories/`` relative to the working
            directory.
        agent_id: the agent name whose memories this handler manages.
            Directory: ``<base>/agents/<sanitized_agent_id>/memories/``.
        check_poisoning: whether to reject writes containing prompt
            injection markers. Defaults to True. Can be disabled for
            tests.
    """

    def __init__(
        self,
        *,
        base_path: str | Path = "backend/data/memories",
        agent_id: str,
        check_poisoning: bool = True,
    ) -> None:
        self._raw_agent_id = agent_id
        self.agent_id = _sanitize_agent_id(agent_id)
        self.base_path = Path(base_path).resolve()
        self.memory_root = (
            self.base_path / "agents" / self.agent_id / "memories"
        ).resolve()
        self.check_poisoning = check_poisoning

        # Create the agent's memory root lazily. Use 0o700 so only the
        # owner can traverse — noop on Windows, meaningful on POSIX.
        try:
            self.memory_root.mkdir(parents=True, exist_ok=True)
            # Try to set restrictive perms but don't fail on Windows
            try:
                self.memory_root.chmod(0o700)
            except (OSError, NotImplementedError):
                pass
        except OSError as exc:
            logger.warning(
                "Could not create memory root %s: %s", self.memory_root, exc
            )

    # ── Path safety ────────────────────────────────────────────────────

    def _resolve_safe_path(self, path_str: str) -> Path:
        """Resolve ``path_str`` and assert it stays inside memory_root.

        The model sends paths rooted at ``/memories`` (the virtual root
        the cookbook uses). We strip the leading ``/memories`` and
        append to the real memory_root.

        Raises:
            PathTraversalError: if the resolved path is not a descendant
                of ``memory_root``.
        """
        if not path_str or not isinstance(path_str, str):
            raise PathTraversalError(f"Invalid path: {path_str!r}")

        # Normalize the virtual root prefix
        normalized = path_str.replace("\\", "/")
        if normalized.startswith("/memories"):
            normalized = normalized[len("/memories"):]
        normalized = normalized.lstrip("/")

        # Reject absolute-looking leftovers
        candidate = (self.memory_root / normalized).resolve()

        try:
            candidate.relative_to(self.memory_root)
        except ValueError as exc:
            raise PathTraversalError(
                f"Path escapes memory root: {path_str!r}"
            ) from exc

        return candidate

    # ── Validation helpers ─────────────────────────────────────────────

    def _assert_file_size(self, content: str) -> None:
        if len(content.encode("utf-8", errors="ignore")) > MAX_FILE_BYTES:
            raise SizeCapError(
                f"File exceeds {MAX_FILE_BYTES} byte cap"
            )

    def _assert_operation_size(self, content: str) -> None:
        if len(content.encode("utf-8", errors="ignore")) > MAX_OPERATION_BYTES:
            raise SizeCapError(
                f"Operation exceeds {MAX_OPERATION_BYTES} byte cap"
            )

    def _assert_no_poisoning(self, content: str) -> None:
        if not self.check_poisoning:
            return
        # L-3 hardening (2026-04-30): normalize before matching so
        # Unicode lookalikes and zero-width insertions can't bypass
        # the markers. See `_normalize_for_poisoning_check` docstring.
        normalized = _normalize_for_poisoning_check(content)
        if _POISONING_RE.search(normalized):
            raise PoisoningDetectedError(
                "Content contains a prompt injection marker; refusing to store"
            )

    def _assert_dir_soft_cap(self) -> None:
        """Best-effort check on total directory size before a write."""
        try:
            total = sum(
                f.stat().st_size
                for f in self.memory_root.rglob("*")
                if f.is_file()
            )
        except OSError:
            return  # cannot check; let it proceed
        if total > MAX_DIR_BYTES:
            raise SizeCapError(
                f"Agent memory directory exceeds {MAX_DIR_BYTES} byte soft cap "
                f"(currently {total}). Delete old files before writing new ones."
            )

    # ── Command handlers ───────────────────────────────────────────────

    def view(self, path: str) -> MemoryToolResponse:
        """List a directory or read a file."""
        try:
            target = self._resolve_safe_path(path)
        except PathTraversalError as exc:
            return MemoryToolResponse(True, str(exc), "view")

        if not target.exists():
            return MemoryToolResponse(
                True,
                f"Not found: {path}. The memory root is initially empty.",
                "view",
            )

        if target.is_dir():
            try:
                entries = sorted(
                    p.name + ("/" if p.is_dir() else "")
                    for p in target.iterdir()
                )
            except OSError as exc:
                return MemoryToolResponse(True, f"Cannot list: {exc}", "view")
            listing = "\n".join(entries) if entries else "(empty directory)"
            return MemoryToolResponse(False, listing, "view")

        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot read: {exc}", "view")

        return MemoryToolResponse(False, text, "view")

    def create(self, path: str, file_text: str) -> MemoryToolResponse:
        """Create a new file (or overwrite an existing one) with content."""
        try:
            target = self._resolve_safe_path(path)
            self._assert_file_size(file_text)
            self._assert_no_poisoning(file_text)
            self._assert_dir_soft_cap()
        except MemoryToolError as exc:
            return MemoryToolResponse(True, str(exc), "create")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file_text, encoding="utf-8")
            try:
                target.chmod(0o600)
            except (OSError, NotImplementedError):
                pass
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot write: {exc}", "create")

        return MemoryToolResponse(
            False, f"File created at {path} ({len(file_text)} chars)", "create"
        )

    def str_replace(
        self, path: str, old_str: str, new_str: str
    ) -> MemoryToolResponse:
        """Replace the first occurrence of ``old_str`` with ``new_str``.

        Errors if the file does not exist, the marker is missing, or
        the marker appears more than once (ambiguous).
        """
        try:
            target = self._resolve_safe_path(path)
            self._assert_operation_size(old_str)
            self._assert_operation_size(new_str)
            self._assert_no_poisoning(new_str)
        except MemoryToolError as exc:
            return MemoryToolResponse(True, str(exc), "str_replace")

        if not target.exists() or not target.is_file():
            return MemoryToolResponse(
                True, f"File not found: {path}", "str_replace"
            )

        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot read: {exc}", "str_replace")

        count = text.count(old_str)
        if count == 0:
            return MemoryToolResponse(
                True,
                f"Marker not found in {path}: {old_str[:80]!r}",
                "str_replace",
            )
        if count > 1:
            return MemoryToolResponse(
                True,
                f"Marker appears {count} times in {path}; cannot disambiguate. "
                f"Add more context to old_str.",
                "str_replace",
            )

        new_text = text.replace(old_str, new_str, 1)

        try:
            self._assert_file_size(new_text)
        except SizeCapError as exc:
            return MemoryToolResponse(True, str(exc), "str_replace")

        try:
            target.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot write: {exc}", "str_replace")

        return MemoryToolResponse(
            False,
            f"Replaced 1 occurrence in {path}",
            "str_replace",
        )

    def insert(
        self, path: str, insert_line: int, insert_text: str
    ) -> MemoryToolResponse:
        """Insert text after ``insert_line`` (1-indexed).

        insert_line=0 inserts at the very beginning of the file.
        """
        try:
            target = self._resolve_safe_path(path)
            self._assert_operation_size(insert_text)
            self._assert_no_poisoning(insert_text)
        except MemoryToolError as exc:
            return MemoryToolResponse(True, str(exc), "insert")

        if not target.exists() or not target.is_file():
            return MemoryToolResponse(
                True, f"File not found: {path}", "insert"
            )

        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot read: {exc}", "insert")

        lines = text.splitlines(keepends=True)
        if insert_line < 0 or insert_line > len(lines):
            return MemoryToolResponse(
                True,
                f"insert_line out of range: {insert_line} (file has {len(lines)} lines)",
                "insert",
            )

        if not insert_text.endswith("\n"):
            insert_text = insert_text + "\n"

        new_lines = lines[:insert_line] + [insert_text] + lines[insert_line:]
        new_text = "".join(new_lines)

        try:
            self._assert_file_size(new_text)
        except SizeCapError as exc:
            return MemoryToolResponse(True, str(exc), "insert")

        try:
            target.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot write: {exc}", "insert")

        return MemoryToolResponse(
            False, f"Inserted after line {insert_line} in {path}", "insert"
        )

    def delete(self, path: str) -> MemoryToolResponse:
        """Remove a file or an empty directory."""
        try:
            target = self._resolve_safe_path(path)
        except PathTraversalError as exc:
            return MemoryToolResponse(True, str(exc), "delete")

        # Refuse to delete the memory root itself
        if target == self.memory_root:
            return MemoryToolResponse(
                True, "Refusing to delete the memory root", "delete"
            )

        if not target.exists():
            return MemoryToolResponse(
                True, f"Not found: {path}", "delete"
            )

        try:
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                # Only delete empty directories to avoid accidents
                try:
                    target.rmdir()
                except OSError:
                    return MemoryToolResponse(
                        True,
                        f"Directory not empty: {path}. Delete files first.",
                        "delete",
                    )
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot delete: {exc}", "delete")

        return MemoryToolResponse(False, f"Deleted {path}", "delete")

    def rename(self, old_path: str, new_path: str) -> MemoryToolResponse:
        """Move / rename a file or directory. Both paths must stay inside
        the memory root."""
        try:
            src = self._resolve_safe_path(old_path)
            dst = self._resolve_safe_path(new_path)
        except PathTraversalError as exc:
            return MemoryToolResponse(True, str(exc), "rename")

        if not src.exists():
            return MemoryToolResponse(
                True, f"Source not found: {old_path}", "rename"
            )
        if dst.exists():
            return MemoryToolResponse(
                True, f"Destination already exists: {new_path}", "rename"
            )

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        except OSError as exc:
            return MemoryToolResponse(True, f"Cannot rename: {exc}", "rename")

        return MemoryToolResponse(
            False, f"Renamed {old_path} -> {new_path}", "rename"
        )

    # ── Dispatch ───────────────────────────────────────────────────────

    def execute(self, command: str, params: dict[str, Any]) -> MemoryToolResponse:
        """Dispatch a command + params dict to the matching handler.

        This is the main entry point. The agent loop receives a
        ``tool_use`` block from Claude whose ``input`` contains a
        ``command`` plus command-specific params. This method routes
        to the right handler method and returns a structured response.

        Unknown commands return an error response rather than raising.
        """
        cmd = (command or "").strip().lower()

        try:
            if cmd == "view":
                return self.view(params.get("path", "/memories"))

            if cmd == "create":
                return self.create(
                    path=params.get("path", ""),
                    file_text=params.get("file_text", ""),
                )

            if cmd == "str_replace":
                return self.str_replace(
                    path=params.get("path", ""),
                    old_str=params.get("old_str", ""),
                    new_str=params.get("new_str", ""),
                )

            if cmd == "insert":
                return self.insert(
                    path=params.get("path", ""),
                    insert_line=int(params.get("insert_line", 0)),
                    insert_text=params.get("insert_text", ""),
                )

            if cmd == "delete":
                return self.delete(params.get("path", ""))

            if cmd == "rename":
                return self.rename(
                    old_path=params.get("old_path", ""),
                    new_path=params.get("new_path", ""),
                )

            return MemoryToolResponse(
                True, f"Unknown command: {command!r}", command or "unknown"
            )

        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("Unexpected error in memory tool dispatch")
            return MemoryToolResponse(
                True,
                f"Internal error handling {command}: {exc}",
                command or "unknown",
            )

    def execute_tool_use(self, tool_use_block: Any) -> MemoryToolResponse:
        """Convenience for the Anthropic tool_use block shape.

        ``tool_use_block`` is the content block from an Anthropic
        response. It has a ``.name`` (should be ``"memory"``) and an
        ``.input`` dict. This method pulls ``command`` from ``.input``
        and passes the rest through to ``execute``.

        Works with either real Anthropic SDK objects or plain dicts
        so the tests can exercise it without mocking the full SDK.
        """
        if hasattr(tool_use_block, "input"):
            input_data = tool_use_block.input
        elif isinstance(tool_use_block, dict):
            input_data = tool_use_block.get("input", {})
        else:
            return MemoryToolResponse(
                True, "Invalid tool_use block shape", "unknown"
            )

        if not isinstance(input_data, dict):
            return MemoryToolResponse(
                True, "tool_use.input is not a dict", "unknown"
            )

        command = input_data.get("command", "")
        params = {k: v for k, v in input_data.items() if k != "command"}
        return self.execute(command, params)
