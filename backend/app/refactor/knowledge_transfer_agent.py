"""Post-modernization knowledge transfer agent — Gap 12.

Closes the 12th and final gap from the ``Platform of the Future`` list
in ``docs/integration/03_future_platform_vision.md`` §Implications:

> 12. Post-modernization knowledge transfer mode — Persistent
>     'tech lead' AI agent that stays after delivery to mentor
>     internal team.

What this module does:

1. **Ingest** an app's knowledge sources — the auto-generated docs
   from Gap 8 (README / ARCHITECTURE / ADR / RUNBOOK / API /
   INTEGRATIONS), any pre-existing markdown docs, and a compact view
   of the git history.

2. **Index** them into a structured Q&A knowledge base — each entry
   has a question, an answer, a source file:line citation, a topic
   tag, and a confidence score.

3. **Answer** natural-language queries from internal developers by
   ranking index entries against the query and returning top-N
   matches with citations. The ranker is a simple keyword-overlap
   scorer, not an LLM call, so the agent runs in-process with zero
   dependencies and zero cost. (An LLM post-pass for narrative
   polish is optional future work.)

4. **Onboarding guide generator** — produces an `ONBOARDING.md`
   that walks a new developer through the codebase in a "first 5
   days" format: day 1 context, day 2 architecture, day 3 integration
   surface, day 4 operational runbook, day 5 pending work.

The agent is DETERMINISTIC in this first cut: TF-IDF-ish keyword
match + source-citation + structured output. No LLM calls, no
external services. This keeps the MVP cheap and auditable, and
leaves room for a future upgrade that wraps the same index with
Claude for more fluent answers.

Why "persistent": the post-modernization tech lead role is a
recurring pattern in real enterprise modernization — internal teams
need someone who can answer "why does the refund flow still call
the old FTP server?" three months after the vendor has left. This
module IS that someone, backed by the documentation bundle that Gap
8 produces and the code history the engine has access to.

Related gaps:
- Gap 1 (multi_lang_scanner): feeds stack detection upstream
- Gap 8 (docs_generator): produces the document bundle this module
  indexes — they are designed to compose
- Gap 11 (observability_bootstrapper): RUNBOOK.md references the
  observability stack, so Q&A about incident response works
- Gap 3 (strangler_planner): Q&A about migration decisions can
  reference the strangler phases

Scope boundary: this module is QUERY-ONLY. It does not modify code,
it does not regenerate docs (that is Gap 8), it does not provision
monitoring, it does not trigger deployments. It is a stateless
knowledge agent.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────

# Max files to walk for raw source indexing (anything beyond this is
# skipped with a warning — the scope is "what the tech lead needs to
# know", not "every file ever").
_MAX_INDEXED_FILES = 500

# Max size of an individual indexed file (beyond this we read only the
# first N KB to avoid eating memory on generated assets).
_MAX_FILE_BYTES = 500_000

# Directories we never index
_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "bower_components",
    "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache",
    "bin", "obj", "target",
    "build", "dist", "out",
    ".next", ".nuxt", ".vercel",
    "coverage", ".coverage",
}

# Files worth a dedicated "source type" tag in the index.
#
# ORDER MATTERS: the first matching pattern wins. ``adr-`` must come
# before ``architecture.md`` because filenames like
# ``ADR-0001-initial-architecture.md`` contain both substrings and we
# want to classify them as ADRs, not architecture docs.
_DOC_FILE_PATTERNS: list[tuple[str, str]] = [
    # (glob_substring, source_type)
    ("adr-", "adr"),
    ("readme.md", "readme"),
    ("architecture.md", "architecture"),
    ("runbook.md", "runbook"),
    ("api.md", "api"),
    ("integrations.md", "integrations"),
    ("contributing.md", "contributing"),
    ("changelog.md", "changelog"),
    ("design-decisions.md", "design_decision"),
    ("deployment.md", "deployment"),
    ("security.md", "security"),
    ("implementation_audit.md", "audit"),
    ("agent_audit.md", "audit"),
]

# Tokens (case-insensitive) that flag a chunk as Q&A-worthy with a
# higher base score. These are the words a tech lead would ask about.
_HIGH_VALUE_TOKENS = {
    "why", "decision", "rationale", "tradeoff", "alternative",
    "risk", "mitigation", "fallback", "rollback", "retry",
    "deploy", "runbook", "incident", "alert", "sla",
    "authentication", "authorization", "security", "encryption",
    "integration", "dependency", "contract",
}


# ── Index entry dataclass ────────────────────────────────────────────────


@dataclass
class IndexEntry:
    """One question-answer pair plus provenance."""

    question: str
    answer: str
    source_file: str
    source_line: int
    source_type: str              # readme / architecture / adr / runbook / etc.
    topic: str = "general"        # high-level classification; default set by _infer_topic
    tokens: list[str] = field(default_factory=list)   # lower-cased search tokens
    confidence: float = 0.5       # 0..1, relative ranking weight

    def to_dict(self) -> dict:
        return asdict(self)


# ── Report dataclass ─────────────────────────────────────────────────────


@dataclass
class KnowledgeTransferReport:
    """Full knowledge transfer agent output for one app."""

    app_name: str
    app_path: str
    generated_at: str
    scanned_files: int = 0
    index_entries: list[IndexEntry] = field(default_factory=list)
    topic_counts: dict[str, int] = field(default_factory=dict)
    sample_queries: list[dict] = field(default_factory=list)
    onboarding_guide: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def total_entries(self) -> int:
        return len(self.index_entries)

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "app_path": self.app_path,
            "generated_at": self.generated_at,
            "scanned_files": self.scanned_files,
            "total_entries": self.total_entries,
            "topic_counts": self.topic_counts,
            "index_entries": [e.to_dict() for e in self.index_entries],
            "sample_queries": list(self.sample_queries),
            "onboarding_guide": self.onboarding_guide,
            "warnings": self.warnings,
        }


@dataclass
class QueryResponse:
    """Answer to a knowledge query."""

    query: str
    matches: list[IndexEntry] = field(default_factory=list)
    top_answer: str = ""
    top_citation: str = ""
    matched_tokens: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "match_count": len(self.matches),
            "top_answer": self.top_answer,
            "top_citation": self.top_citation,
            "matched_tokens": self.matched_tokens,
            "matches": [e.to_dict() for e in self.matches],
        }


# ── Source-type detection ────────────────────────────────────────────────


def _classify_source(file_path: Path) -> str:
    """Return the source_type tag for a file, or 'other' if unmatched."""
    name = file_path.name.lower()
    full = str(file_path).lower().replace("\\", "/")
    for needle, source_type in _DOC_FILE_PATTERNS:
        if needle in name or needle in full:
            return source_type
    if name.endswith(".md"):
        return "doc"
    return "other"


# ── Tokenization for the ranker ──────────────────────────────────────────

# Simple word tokenizer that lowercases and strips punctuation. Keeps
# alphanumeric tokens >= 3 chars. No stemming, no stopword removal
# (kept deliberately simple for auditability).

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]{2,}")


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


# ── Index building ──────────────────────────────────────────────────────


def _split_into_qa_candidates(
    content: str, file_path: str, source_type: str
) -> list[IndexEntry]:
    """Slice a markdown document into Q&A candidate chunks.

    Heuristic: each ``##`` or ``###`` heading starts a new chunk. The
    heading becomes the question, the following paragraphs become the
    answer. If no headings exist (e.g., a plain README), split into
    paragraph-sized chunks of ~3 paragraphs each.
    """
    entries: list[IndexEntry] = []

    # Split on heading markers
    heading_re = re.compile(r"^(#{2,6})\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(content))

    if not matches:
        # No headings — slice into paragraph chunks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            return entries
        # Group paragraphs in triples for non-trivial answers
        chunk_size = 3
        for i in range(0, len(paragraphs), chunk_size):
            chunk = "\n\n".join(paragraphs[i : i + chunk_size])
            if not chunk:
                continue
            first_line = paragraphs[i].splitlines()[0] if paragraphs[i] else ""
            question = first_line[:120] or "General context"
            entry = IndexEntry(
                question=question,
                answer=chunk[:2000],
                source_file=file_path,
                source_line=1,  # paragraphs are not line-indexed here
                source_type=source_type,
                topic=_infer_topic(question + " " + chunk),
                tokens=_tokenize(question + " " + chunk),
            )
            entries.append(entry)
        return entries

    for idx, match in enumerate(matches):
        heading_level = len(match.group(1))
        question = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        answer_raw = content[start:end].strip()
        # Strip sub-subheadings from the answer to keep chunks tight
        answer_clean = "\n".join(
            line for line in answer_raw.splitlines() if not line.startswith("###")
        )
        if not question and not answer_clean:
            continue

        # Compute the approximate line number of the heading
        line_number = content.count("\n", 0, match.start()) + 1

        # Confidence: headings at level 2 are higher-value than level 4
        confidence = max(0.3, 1.0 - 0.15 * (heading_level - 2))

        # Question rephrasing: if the heading is a noun phrase like
        # "Architecture", prepend "What is the" for a more natural Q.
        if not question.lower().startswith(
            ("how", "what", "why", "when", "where", "who", "which")
        ):
            question_phrased = f"What is the {question.lower()}?"
        else:
            question_phrased = question if question.endswith("?") else question + "?"

        entry = IndexEntry(
            question=question_phrased,
            answer=answer_clean[:2000],
            source_file=file_path,
            source_line=line_number,
            source_type=source_type,
            topic=_infer_topic(question + " " + answer_clean),
            tokens=_tokenize(question + " " + answer_clean),
            confidence=confidence,
        )
        entries.append(entry)

    return entries


def _infer_topic(text: str) -> str:
    """Assign a coarse topic label based on keyword presence."""
    lowered = text.lower()
    if any(k in lowered for k in ("deploy", "rollback", "render", "vercel", "ci/cd", "pipeline")):
        return "deployment"
    if any(k in lowered for k in ("security", "auth", "encrypt", "jwt", "owasp", "pii", "compliance")):
        return "security"
    if any(k in lowered for k in ("integration", "api", "endpoint", "http", "ftp", "kafka")):
        return "integrations"
    if any(k in lowered for k in ("architecture", "c4", "context", "container", "component", "diagram")):
        return "architecture"
    if any(k in lowered for k in ("runbook", "incident", "alert", "sla", "oncall", "recovery")):
        return "operations"
    if any(k in lowered for k in ("refactor", "strangler", "legacy", "wrap", "migrate")):
        return "refactor"
    if any(k in lowered for k in ("adr", "decision", "rationale", "tradeoff", "alternative")):
        return "decisions"
    if any(k in lowered for k in ("test", "unit", "integration test", "pytest", "coverage")):
        return "testing"
    return "general"


# ── Repository walk ─────────────────────────────────────────────────────


def _iter_indexable_files(root: Path):
    """Yield files worth adding to the index.

    Prioritizes .md files (documentation). If we are still under
    _MAX_INDEXED_FILES after walking all .md, also include any
    top-level code file that could contain a module-level docstring
    — but bounded by the cap.
    """
    md_files: list[Path] = []
    other_files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        ext = path.suffix.lower()
        if ext == ".md":
            md_files.append(path)
        elif ext in (".py", ".cs", ".java", ".go", ".rs"):
            other_files.append(path)

    # Stable ordering by path for deterministic output
    md_files.sort()
    other_files.sort()

    yielded = 0
    for path in md_files:
        if yielded >= _MAX_INDEXED_FILES:
            return
        yield path
        yielded += 1

    for path in other_files:
        if yielded >= _MAX_INDEXED_FILES:
            return
        yield path
        yielded += 1


def _extract_module_docstring(content: str) -> str:
    """Return the module-level docstring if the file has one, else ''."""
    # Python: triple-quoted string at the start
    py_match = re.match(r'^\s*("""|\'\'\')(.*?)(\1)', content, re.DOTALL)
    if py_match:
        return py_match.group(2).strip()
    # C#/Java: leading // or /** block
    lines = content.splitlines()
    comment_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            comment_lines.append(stripped.lstrip("/*").strip())
        elif stripped == "" and comment_lines:
            continue
        else:
            break
    if comment_lines:
        return "\n".join(comment_lines).strip()
    return ""


# ── Git history sampling ────────────────────────────────────────────────


def _sample_git_history(root: Path, max_commits: int = 50) -> list[IndexEntry]:
    """Capture a compact slice of the git history as searchable entries.

    Runs ``git log`` inside the repo and converts each recent commit
    into an IndexEntry with the commit message as the answer. Commits
    that mention "why", "decision", "rationale", etc. get a confidence
    bump.

    Gracefully degrades if git is unavailable or the path is not a
    repo — returns [] without raising.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                f"--max-count={max_commits}",
                "--pretty=format:%H|%an|%ad|%s|%b%x1e",
                "--date=short",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    if result.returncode != 0:
        return []

    entries: list[IndexEntry] = []
    # Records are separated by record separator char (0x1e)
    records = [r for r in result.stdout.split("\x1e") if r.strip()]
    for record in records:
        parts = record.split("|", 4)
        if len(parts) < 5:
            continue
        sha, author, date, subject, body = parts
        commit_text = f"{subject}\n\n{body}".strip()
        question = f"Why was commit {sha[:8]} made?"
        entry = IndexEntry(
            question=question,
            answer=(
                f"**{subject}**\n\n"
                f"Author: {author}\n"
                f"Date: {date}\n\n"
                f"{body.strip()[:1500]}"
            ),
            source_file=f"git:{sha[:12]}",
            source_line=0,
            source_type="commit",
            topic=_infer_topic(commit_text),
            tokens=_tokenize(commit_text),
            confidence=0.4 + (0.2 if any(k in commit_text.lower() for k in _HIGH_VALUE_TOKENS) else 0),
        )
        entries.append(entry)
    return entries


# ── Indexer ─────────────────────────────────────────────────────────────


def build_knowledge_index(
    app_name: str, app_path: str, include_git_history: bool = True
) -> KnowledgeTransferReport:
    """Walk the repo, ingest docs + git history, build the index.

    Args:
        app_name: human-readable name used in the report
        app_path: filesystem path to walk
        include_git_history: if True and git is available, sample the
            last 50 commits into the index

    Returns:
        KnowledgeTransferReport with ``index_entries`` populated.

    Raises:
        FileNotFoundError: if ``app_path`` does not exist.
    """
    root = Path(app_path)
    if not root.exists():
        raise FileNotFoundError(f"App path does not exist: {app_path}")

    now = datetime.now(timezone.utc).isoformat()
    report = KnowledgeTransferReport(
        app_name=app_name, app_path=app_path, generated_at=now
    )

    scanned = 0
    for path in _iter_indexable_files(root):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            report.warnings.append(f"Cannot read {path}: {exc}")
            continue

        if len(text.encode("utf-8", errors="ignore")) > _MAX_FILE_BYTES:
            text = text[:_MAX_FILE_BYTES]
            report.warnings.append(f"Truncated oversized file: {path}")

        rel = str(path.relative_to(root)).replace("\\", "/")

        if path.suffix.lower() == ".md":
            source_type = _classify_source(path)
            entries = _split_into_qa_candidates(text, rel, source_type)
            report.index_entries.extend(entries)
        else:
            # Code files: extract module docstring only
            docstring = _extract_module_docstring(text)
            if docstring:
                entry = IndexEntry(
                    question=f"What does the module {path.name} do?",
                    answer=docstring[:2000],
                    source_file=rel,
                    source_line=1,
                    source_type="code_docstring",
                    topic=_infer_topic(docstring),
                    tokens=_tokenize(docstring),
                    confidence=0.5,
                )
                report.index_entries.append(entry)

    report.scanned_files = scanned

    if include_git_history:
        git_entries = _sample_git_history(root)
        report.index_entries.extend(git_entries)

    # Topic counts
    counts: dict[str, int] = {}
    for entry in report.index_entries:
        counts[entry.topic] = counts.get(entry.topic, 0) + 1
    report.topic_counts = counts

    # Sample queries derived from topic coverage — these are
    # suggestions the UI can surface as "things you might ask the
    # tech lead"
    sample_q: list[dict] = []
    for topic, count in sorted(counts.items(), key=lambda kv: -kv[1])[:6]:
        sample_q.append(
            {
                "topic": topic,
                "count": count,
                "example": _example_query_for_topic(topic),
            }
        )
    report.sample_queries = sample_q

    # Onboarding guide
    report.onboarding_guide = _render_onboarding_guide(report)

    return report


def _example_query_for_topic(topic: str) -> str:
    return {
        "deployment": "How do I deploy this app to production?",
        "security": "What authentication mechanism does this app use?",
        "integrations": "What external systems does this app depend on?",
        "architecture": "What are the major modules and how do they fit together?",
        "operations": "What should I do if the batch job fails overnight?",
        "refactor": "What refactoring decisions were made and why?",
        "decisions": "What architecture decision records exist for this app?",
        "testing": "How do I run the tests?",
        "general": "What does this app do?",
    }.get(topic, "Tell me about this app")


# ── Query engine ────────────────────────────────────────────────────────


def query_knowledge(
    report: KnowledgeTransferReport, query: str, top_n: int = 5
) -> QueryResponse:
    """Rank index entries against a natural-language query.

    Scoring (deterministic, no LLM):
      - Token overlap between the query and the entry's tokens list
      - Bonus for high-value tokens like "why", "decision", "rationale"
      - Multiplied by the entry's confidence score
      - Ties broken by source_type priority (adr > architecture > runbook > ...)

    Returns a QueryResponse with the top ``top_n`` entries and a
    top_answer field set to the highest-scoring entry's answer.
    """
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return QueryResponse(query=query)

    source_priority = {
        "adr": 5,
        "architecture": 4,
        "runbook": 4,
        "design_decision": 4,
        "integrations": 3,
        "api": 3,
        "security": 3,
        "readme": 2,
        "contributing": 2,
        "commit": 1,
        "code_docstring": 1,
        "doc": 1,
        "other": 0,
    }

    scored: list[tuple[float, IndexEntry]] = []
    for entry in report.index_entries:
        entry_tokens = set(entry.tokens)
        overlap = len(q_tokens & entry_tokens)
        if overlap == 0:
            continue
        high_value_bonus = len(q_tokens & _HIGH_VALUE_TOKENS) * 0.5
        base = float(overlap) + high_value_bonus
        score = base * entry.confidence
        scored.append((score, entry))

    # Sort by score desc, then source priority, then entry question for
    # determinism
    scored.sort(
        key=lambda pair: (
            -pair[0],
            -source_priority.get(pair[1].source_type, 0),
            pair[1].question,
        )
    )

    top_entries = [entry for _, entry in scored[:top_n]]
    top_answer = top_entries[0].answer if top_entries else ""
    top_citation = (
        f"{top_entries[0].source_file}:{top_entries[0].source_line}"
        if top_entries and top_entries[0].source_line
        else (top_entries[0].source_file if top_entries else "")
    )
    matched_tokens = sorted(q_tokens & set(_HIGH_VALUE_TOKENS))

    return QueryResponse(
        query=query,
        matches=top_entries,
        top_answer=top_answer,
        top_citation=top_citation,
        matched_tokens=matched_tokens,
    )


# ── Onboarding guide renderer ───────────────────────────────────────────


def _render_onboarding_guide(report: KnowledgeTransferReport) -> str:
    """Produce a "first 5 days" onboarding walkthrough in markdown.

    Pulls content from the index by source_type to populate each day:

    - Day 1: README / context
    - Day 2: ARCHITECTURE + ADRs
    - Day 3: API + INTEGRATIONS
    - Day 4: RUNBOOK + deployment
    - Day 5: pending work (from commit history + warnings)
    """
    by_type: dict[str, list[IndexEntry]] = {}
    for entry in report.index_entries:
        by_type.setdefault(entry.source_type, []).append(entry)

    def _section(header: str, types: list[str]) -> list[str]:
        lines: list[str] = [f"## {header}", ""]
        found = False
        for t in types:
            for entry in by_type.get(t, [])[:3]:
                found = True
                lines.append(f"- **{entry.question}** ({entry.source_file}:{entry.source_line})")
        if not found:
            lines.append("_(No relevant entries indexed — ask the team directly.)_")
        lines.append("")
        return lines

    out: list[str] = [
        f"# Onboarding — {report.app_name}",
        "",
        (
            "> Auto-generated onboarding walkthrough for new developers. "
            f"Built from {report.total_entries} indexed entries across "
            f"{report.scanned_files} scanned files. "
            f"Last generated: {report.generated_at}."
        ),
        "",
        "This is a first-pass walkthrough — refine with a human tech lead.",
        "",
    ]

    out.extend(_section("Day 1 — Context and stack", ["readme", "doc"]))
    out.extend(_section("Day 2 — Architecture and decisions", ["architecture", "adr", "design_decision"]))
    out.extend(_section("Day 3 — API and integrations", ["api", "integrations"]))
    out.extend(_section("Day 4 — Runbook and deployment", ["runbook", "deployment", "operations"]))

    # Day 5: recent commits as "pending / in-flight work"
    out.append("## Day 5 — Recent work and in-flight changes")
    out.append("")
    commits = by_type.get("commit", [])[:5]
    if commits:
        for c in commits:
            first_line = c.answer.splitlines()[0] if c.answer else c.question
            out.append(f"- `{c.source_file}` — {first_line[:120]}")
    else:
        out.append("_(No commit history indexed — run `git log` manually.)_")
    out.append("")

    if report.warnings:
        out.append("## Warnings from the index build")
        out.append("")
        for w in report.warnings[:5]:
            out.append(f"- {w}")
        out.append("")

    return "\n".join(out)


# ── Public entry point ──────────────────────────────────────────────────


def run_knowledge_transfer(
    app_name: str, app_path: str, include_git_history: bool = True
) -> KnowledgeTransferReport:
    """Build the full knowledge transfer report for an app.

    Convenience wrapper that calls ``build_knowledge_index`` and
    returns the populated report. Use ``query_knowledge(report, q)``
    afterwards to answer individual questions.
    """
    return build_knowledge_index(
        app_name=app_name,
        app_path=app_path,
        include_git_history=include_git_history,
    )
