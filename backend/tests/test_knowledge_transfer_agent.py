"""Tests for Gap 12 — Post-modernization knowledge transfer agent.

Covers the indexer, the Q&A splitter for markdown, the source-type
classifier, the topic inferencer, the ranker, the onboarding guide
renderer, and the end-to-end build_knowledge_index orchestrator.

All tests use tmp_path so each runs against an isolated temp repo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.refactor.knowledge_transfer_agent import (
    IndexEntry,
    KnowledgeTransferReport,
    QueryResponse,
    _classify_source,
    _extract_module_docstring,
    _infer_topic,
    _split_into_qa_candidates,
    _tokenize,
    build_knowledge_index,
    query_knowledge,
    run_knowledge_transfer,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    return tmp_path


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ── Tokenizer ─────────────────────────────────────────────────────────────


def test_tokenize_basic():
    tokens = _tokenize("The quick brown fox jumps over the lazy dog")
    assert "the" in tokens
    assert "quick" in tokens
    assert "fox" in tokens


def test_tokenize_lowercases():
    assert _tokenize("HTTP API")[0] == "http"


def test_tokenize_skips_short_tokens():
    tokens = _tokenize("a b cd efg")
    assert "cd" not in tokens
    assert "efg" in tokens


def test_tokenize_strips_punctuation():
    tokens = _tokenize("Hello, world! How are you?")
    assert "hello" in tokens
    assert "world" in tokens


# ── Source classifier ────────────────────────────────────────────────────


def test_classify_readme():
    assert _classify_source(Path("README.md")) == "readme"


def test_classify_architecture():
    assert _classify_source(Path("docs/ARCHITECTURE.md")) == "architecture"


def test_classify_adr():
    assert _classify_source(Path("docs/ADR-0001-initial-architecture.md")) == "adr"


def test_classify_runbook():
    assert _classify_source(Path("RUNBOOK.md")) == "runbook"


def test_classify_generic_md():
    assert _classify_source(Path("random.md")) == "doc"


def test_classify_non_md():
    assert _classify_source(Path("src/app.py")) == "other"


# ── Topic inference ──────────────────────────────────────────────────────


def test_topic_deployment():
    assert _infer_topic("How to deploy to Render production") == "deployment"


def test_topic_security():
    assert _infer_topic("JWT authentication for PII handling") == "security"


def test_topic_integrations():
    assert _infer_topic("FTP endpoint for partner file drop") == "integrations"


def test_topic_architecture():
    assert _infer_topic("C4 component diagram for the order service") == "architecture"


def test_topic_general_fallback():
    assert _infer_topic("hello world") == "general"


# ── Q&A splitter ─────────────────────────────────────────────────────────


def test_qa_splitter_headings():
    content = """# Title

## Why we chose FastAPI

Because of the async support and automatic OpenAPI generation.

## How deployment works

We deploy to Render via auto-deploy from master.
"""
    entries = _split_into_qa_candidates(content, "README.md", "readme")
    assert len(entries) == 2
    # Questions are rephrased when the heading is a noun phrase
    questions = [e.question for e in entries]
    assert any("why we chose fastapi" in q.lower() for q in questions)
    assert any("how deployment works" in q.lower() for q in questions)


def test_qa_splitter_no_headings_paragraphs():
    content = (
        "This application reconciles invoices.\n\n"
        "It reads BSP files and writes to Oracle.\n\n"
        "It runs 3-4 times per month."
    )
    entries = _split_into_qa_candidates(content, "README.md", "readme")
    assert len(entries) >= 1
    # The first entry should contain the paragraph content
    assert "reconciles" in entries[0].answer


def test_qa_splitter_line_numbers():
    content = "# T\n\n## H1\n\nA1\n\n## H2\n\nA2\n"
    entries = _split_into_qa_candidates(content, "f.md", "doc")
    # Second heading is on line 7 (1-indexed)
    h2 = [e for e in entries if "h2" in e.question.lower()]
    assert h2
    assert h2[0].source_line == 7


def test_qa_splitter_confidence_by_heading_level():
    content = "## Level 2\n\nhi\n\n#### Level 4\n\nbye\n"
    entries = _split_into_qa_candidates(content, "f.md", "doc")
    by_q = {e.question.lower(): e for e in entries}
    # Level 2 should have higher confidence than level 4
    l2 = [v for k, v in by_q.items() if "level 2" in k][0]
    l4 = [v for k, v in by_q.items() if "level 4" in k][0]
    assert l2.confidence > l4.confidence


def test_qa_splitter_preserves_questions_ending_with_qmark():
    content = "## Why this?\n\nBecause.\n"
    entries = _split_into_qa_candidates(content, "f.md", "doc")
    assert entries[0].question == "Why this?"


def test_qa_splitter_empty_content():
    assert _split_into_qa_candidates("", "f.md", "doc") == []


# ── Module docstring extraction ──────────────────────────────────────────


def test_extract_docstring_python_triple_quote():
    content = '"""This is a module.\n\nIt does things."""\n\nimport os\n'
    result = _extract_module_docstring(content)
    assert "This is a module" in result
    assert "does things" in result


def test_extract_docstring_csharp_comments():
    content = """// First comment
// Second comment
// Third comment

using System;

class Foo {}
"""
    result = _extract_module_docstring(content)
    assert "First comment" in result


def test_extract_docstring_none_returns_empty():
    assert _extract_module_docstring("import os\nprint('hi')\n") == ""


# ── build_knowledge_index end-to-end ────────────────────────────────────


def test_build_index_raises_on_missing_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_knowledge_index("x", str(tmp_path / "nope"))


def test_build_index_empty_repo(tmp_repo: Path):
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    assert report.app_name == "alpha"
    assert report.scanned_files == 0
    assert report.total_entries == 0


def test_build_index_indexes_readme(tmp_repo: Path):
    _write(tmp_repo, "README.md", """
# MyApp

## Why FastAPI

Because async and OpenAPI.

## How to deploy

Run vercel --prod.
""")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    assert report.scanned_files >= 1
    assert report.total_entries >= 2
    types = {e.source_type for e in report.index_entries}
    assert "readme" in types


def test_build_index_counts_by_topic(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# App\n\n## How to deploy\n\nUse Render.\n")
    _write(tmp_repo, "SECURITY.md", "# Security\n\n## Authentication\n\nJWT tokens.\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    assert "deployment" in report.topic_counts or "general" in report.topic_counts
    assert report.topic_counts.get("security", 0) > 0


def test_build_index_extracts_code_docstring(tmp_repo: Path):
    _write(tmp_repo, "src/app.py", '"""This module handles orders.\n\nVery important."""\nimport os\n')
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    # The code file should have its docstring indexed
    code_entries = [e for e in report.index_entries if e.source_type == "code_docstring"]
    assert code_entries
    assert "orders" in code_entries[0].answer.lower()


def test_build_index_skips_node_modules(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# App\n")
    _write(tmp_repo, "node_modules/x/README.md", "# fake module\n\n## something\n\nignore\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    files_scanned = {e.source_file for e in report.index_entries}
    assert not any("node_modules" in p for p in files_scanned)


def test_build_index_populates_sample_queries(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# App\n\n## Deployment\n\nRender.\n")
    _write(tmp_repo, "SECURITY.md", "# S\n\n## Auth\n\nJWT.\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    assert report.sample_queries
    # Each sample should have topic, count, example
    for s in report.sample_queries:
        assert "topic" in s
        assert "count" in s
        assert "example" in s


def test_build_index_generates_onboarding_guide(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# App\n\n## Day 1\n\nContext.\n")
    _write(tmp_repo, "ARCHITECTURE.md", "# Arch\n\n## Components\n\nBreakdown.\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    guide = report.onboarding_guide
    assert "# Onboarding" in guide
    assert "Day 1" in guide
    assert "Day 5" in guide


# ── query_knowledge ─────────────────────────────────────────────────────


def test_query_empty_index_returns_empty():
    report = KnowledgeTransferReport(
        app_name="x", app_path="/x", generated_at="2026-04-10T00:00:00"
    )
    result = query_knowledge(report, "anything")
    assert isinstance(result, QueryResponse)
    assert result.matches == []
    assert result.top_answer == ""


def test_query_empty_string_returns_empty():
    report = KnowledgeTransferReport(
        app_name="x", app_path="/x", generated_at="2026-04-10T00:00:00"
    )
    report.index_entries = [
        IndexEntry(
            question="Q",
            answer="A",
            source_file="f.md",
            source_line=1,
            source_type="readme",
            tokens=["hello"],
        )
    ]
    result = query_knowledge(report, "")
    assert result.matches == []


def test_query_returns_matching_entry(tmp_repo: Path):
    _write(tmp_repo, "README.md", """
# App

## How to deploy to production

Run `vercel --prod` from the frontend directory.

## How to test locally

Use pytest.
""")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    result = query_knowledge(report, "how do I deploy the app")
    assert len(result.matches) >= 1
    # The top match should be about deployment
    assert "deploy" in result.matches[0].question.lower() or "deploy" in result.matches[0].answer.lower()


def test_query_ranks_adr_higher_than_readme(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# App\n\n## Decision about database\n\nWe use Postgres.\n")
    _write(tmp_repo, "ADR-0001-db.md", "# ADR\n\n## Decision about database\n\nChose Postgres because of pgvector.\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    result = query_knowledge(report, "decision about database")
    # ADR should rank first due to source_priority
    assert result.matches
    top_types = [m.source_type for m in result.matches]
    if len(top_types) >= 2:
        assert top_types[0] == "adr" or top_types.index("adr") < top_types.index("readme")


def test_query_returns_top_n_cap(tmp_repo: Path):
    md = "# App\n"
    for i in range(20):
        md += f"\n## Topic {i} about deploy\n\nSomething about deploy {i}.\n"
    _write(tmp_repo, "README.md", md)
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    result = query_knowledge(report, "deploy", top_n=3)
    assert len(result.matches) <= 3


def test_query_top_citation_includes_file_and_line(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# A\n\n## Deployment\n\nRender.\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    result = query_knowledge(report, "deployment")
    assert result.top_citation
    assert "README.md" in result.top_citation


def test_query_matched_tokens_high_value():
    report = KnowledgeTransferReport(
        app_name="x", app_path="/x", generated_at="2026-04-10T00:00:00"
    )
    report.index_entries = [
        IndexEntry(
            question="Why this decision",
            answer="Because of rationale",
            source_file="adr.md",
            source_line=1,
            source_type="adr",
            tokens=["decision", "rationale", "because"],
        )
    ]
    result = query_knowledge(report, "why is the decision made and what is the rationale")
    assert "why" in result.matched_tokens
    assert "decision" in result.matched_tokens
    assert "rationale" in result.matched_tokens


# ── to_dict serialization ────────────────────────────────────────────────


def test_report_to_dict_is_json_serializable(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# A\n\n## X\n\ny\n")
    report = build_knowledge_index(
        "alpha", str(tmp_repo), include_git_history=False
    )
    d = report.to_dict()
    assert "app_name" in d
    assert "index_entries" in d
    assert "topic_counts" in d
    assert "onboarding_guide" in d
    # Round-trip JSON
    assert json.loads(json.dumps(d)) == d


def test_query_response_to_dict():
    report = KnowledgeTransferReport(
        app_name="x", app_path="/x", generated_at="2026-04-10T00:00:00"
    )
    report.index_entries = [
        IndexEntry(
            question="Q",
            answer="A",
            source_file="f.md",
            source_line=1,
            source_type="readme",
            tokens=["alpha"],
        )
    ]
    result = query_knowledge(report, "alpha")
    d = result.to_dict()
    assert "query" in d
    assert "match_count" in d
    assert "matches" in d
    json.dumps(d)  # should not raise


# ── run_knowledge_transfer convenience ──────────────────────────────────


def test_run_knowledge_transfer_is_wrapper(tmp_repo: Path):
    _write(tmp_repo, "README.md", "# A\n")
    report = run_knowledge_transfer(
        "alpha", str(tmp_repo), include_git_history=False
    )
    assert isinstance(report, KnowledgeTransferReport)
    assert report.app_name == "alpha"
