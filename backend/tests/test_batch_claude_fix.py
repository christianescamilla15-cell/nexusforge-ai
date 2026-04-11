"""Tests for Feature 1 — batch_pipeline._fix_claude_batch wiring.

Verifies:
- Response parser (_extract_fixed_code) handles fenced code, malformed input,
  prose, and edge cases.
- Prompt builder (_build_claude_fix_prompt) includes all required fields.
- _fix_claude_batch happy path: mocked router returns a fenced code block,
  function returns (fixed, count, tokens, cost).
- _fix_claude_batch fallback path: mocked router raises, function falls
  through to _fix_ollama (also mocked) and then _fix_deterministic.
- _fix_claude_batch passes context_management to the router (Feature 1 wiring).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.refactor.batch_pipeline import BatchRemediationPipeline, WorkUnit


# ---------- _extract_fixed_code ----------

def test_extract_fenced_code_with_lang():
    text = "Here is the fix:\n```python\nprint('ok')\nreturn 42\n```\ndone"
    assert BatchRemediationPipeline._extract_fixed_code(text) == "print('ok')\nreturn 42"


def test_extract_fenced_code_without_lang():
    text = "```\nraw content\nhere\n```"
    assert BatchRemediationPipeline._extract_fixed_code(text) == "raw content\nhere"


def test_extract_fenced_code_with_hyphenated_lang():
    text = "```c-sharp\npublic class Foo {}\n```"
    assert BatchRemediationPipeline._extract_fixed_code(text) == "public class Foo {}"


def test_extract_returns_none_for_empty():
    assert BatchRemediationPipeline._extract_fixed_code("") is None
    assert BatchRemediationPipeline._extract_fixed_code("   \n  ") is None


def test_extract_returns_none_for_prose_response():
    text = "I would fix this by using parameterized queries instead of string concat."
    assert BatchRemediationPipeline._extract_fixed_code(text) is None


def test_extract_returns_none_for_instructional_prose():
    text = "Here is how you should fix it: step 1..."
    assert BatchRemediationPipeline._extract_fixed_code(text) is None


def test_extract_raw_code_fallback():
    """Model forgot the fence but returned plausible code."""
    text = "def fixed():\n    return 1"
    assert BatchRemediationPipeline._extract_fixed_code(text) == "def fixed():\n    return 1"


# ---------- _build_claude_fix_prompt ----------

def _pipeline(tmp_path=None):
    return BatchRemediationPipeline(project_root=str(tmp_path or "."), dry_run=True)


def test_prompt_includes_file_and_language():
    p = _pipeline()
    unit = WorkUnit(
        id="B1-0",
        file_path="backend/app/db/query.py",
        app="backend",
        issues=[{"cwe": "CWE-89", "severity": "critical", "description": "SQL injection",
                 "line": 42, "remediation": "Use parameterized query"}],
    )
    prompt = p._build_claude_fix_prompt("SELECT * FROM users WHERE id = '" + "1'", unit)
    assert "backend/app/db/query.py" in prompt
    assert "python" in prompt.lower()
    assert "CWE-89" in prompt
    assert "CRITICAL" in prompt
    assert "SQL injection" in prompt
    assert "Use parameterized query" in prompt
    assert "ORIGINAL FILE CONTENT" in prompt
    assert "```python" in prompt


def test_prompt_handles_unknown_extension():
    p = _pipeline()
    unit = WorkUnit(id="X", file_path="data/config.xyz", app="", issues=[])
    prompt = p._build_claude_fix_prompt("<xml/>", unit)
    assert "data/config.xyz" in prompt
    assert "unknown" in prompt  # lang fallback
    assert "(no structured issues provided)" in prompt


def test_prompt_enumerates_multiple_issues():
    p = _pipeline()
    unit = WorkUnit(
        id="B1-1",
        file_path="src/auth.cs",
        app="identity",
        issues=[
            {"cwe": "CWE-89", "severity": "high", "description": "SQLi in login",
             "line": 10, "remediation": "Parameterize"},
            {"cwe": "CWE-798", "severity": "critical", "description": "Hardcoded secret",
             "line": 22, "remediation": "Move to env var"},
            {"cwe": "CWE-327", "severity": "medium", "description": "Weak hash",
             "line": 55, "remediation": "Use SHA-256"},
        ],
    )
    prompt = p._build_claude_fix_prompt("// code here", unit)
    assert "ISSUES TO FIX (3 total)" in prompt
    assert "1. [CWE-89]" in prompt
    assert "2. [CWE-798]" in prompt
    assert "3. [CWE-327]" in prompt
    assert "csharp" in prompt.lower()


# ---------- _fix_claude_batch (happy path) ----------

@pytest.mark.asyncio
async def test_fix_claude_batch_happy_path():
    """Router returns a valid fenced response; function returns the fixed code."""
    p = _pipeline()
    unit = WorkUnit(
        id="B1-0",
        file_path="src/query.py",
        app="backend",
        issues=[{"cwe": "CWE-89", "severity": "high", "description": "SQLi",
                 "line": 5, "remediation": "Parameterize"}],
    )
    original = "def q(x):\n    return 'SELECT ' + x"
    expected_fixed = "def q(x):\n    return 'SELECT %s'  # param=x"

    fake_resp = MagicMock()
    fake_resp.text = f"```python\n{expected_fixed}\n```"
    fake_resp.tokens_input = 120
    fake_resp.tokens_output = 40
    fake_resp.cost_usd = 0.0025

    mock_router = MagicMock()
    mock_router.chat = AsyncMock(return_value=fake_resp)

    with patch("app.llm.router.get_router", return_value=mock_router):
        fixed, count, tokens, cost = await p._fix_claude_batch(original, unit)

    assert fixed == expected_fixed
    assert count == 1  # 1 issue in unit.issues
    assert tokens == 160
    assert cost == pytest.approx(0.0025)


@pytest.mark.asyncio
async def test_fix_claude_batch_passes_context_management_to_router():
    """Feature 1 wiring check: the router.chat call must include
    context_management with a clear_tool_uses_20250919 edit."""
    p = _pipeline()
    unit = WorkUnit(id="B1-0", file_path="src/x.py", app="", issues=[])
    original = "x = 1\n" * 20  # long enough to exceed the 30% sanity check

    fake_resp = MagicMock()
    fake_resp.text = f"```python\n{original}\n```"
    fake_resp.tokens_input = 100
    fake_resp.tokens_output = 20
    fake_resp.cost_usd = 0.0

    mock_router = MagicMock()
    mock_router.chat = AsyncMock(return_value=fake_resp)

    with patch("app.llm.router.get_router", return_value=mock_router):
        await p._fix_claude_batch(original, unit)

    mock_router.chat.assert_awaited_once()
    call_kwargs = mock_router.chat.await_args.kwargs
    assert "context_management" in call_kwargs
    ctx = call_kwargs["context_management"]
    assert ctx["edits"][0]["type"] == "clear_tool_uses_20250919"
    assert call_kwargs["agent_name"] == "RefactorFixerAgent"


# ---------- _fix_claude_batch (fallback paths) ----------

@pytest.mark.asyncio
async def test_fix_claude_batch_falls_back_on_malformed_response():
    """If Claude returns prose (no code fence), fall back to Ollama."""
    p = _pipeline()
    unit = WorkUnit(
        id="B1-0",
        file_path="src/query.py",
        app="",
        issues=[{"cwe": "CWE-89", "severity": "high", "description": "SQLi", "line": 1, "remediation": "fix"}],
    )
    original = "def q():\n    return 1\n" * 10  # non-trivial

    fake_resp = MagicMock()
    fake_resp.text = "I would recommend using parameterized queries, which are safer than string concatenation."
    fake_resp.tokens_input = 50
    fake_resp.tokens_output = 20
    fake_resp.cost_usd = 0.0

    mock_router = MagicMock()
    mock_router.chat = AsyncMock(return_value=fake_resp)

    # Mock _fix_ollama so we can verify it was invoked
    async def fake_ollama(code, u):
        return code + "\n# ollama fixed", 1, 0

    with patch("app.llm.router.get_router", return_value=mock_router), \
         patch.object(p, "_fix_ollama", new=AsyncMock(side_effect=fake_ollama)):
        fixed, count, tokens, cost = await p._fix_claude_batch(original, unit)

    assert "# ollama fixed" in fixed
    assert count == 1
    assert cost == 0.0


@pytest.mark.asyncio
async def test_fix_claude_batch_falls_back_on_router_exception():
    """If router.chat raises, _fix_claude_batch falls back gracefully."""
    p = _pipeline()
    unit = WorkUnit(id="B1-0", file_path="src/x.py", app="", issues=[])
    original = "x = 1"

    mock_router = MagicMock()
    mock_router.chat = AsyncMock(side_effect=RuntimeError("all providers failed"))

    async def fake_ollama(code, u):
        return code + "\n# from ollama", 0, 0

    with patch("app.llm.router.get_router", return_value=mock_router), \
         patch.object(p, "_fix_ollama", new=AsyncMock(side_effect=fake_ollama)):
        fixed, count, tokens, cost = await p._fix_claude_batch(original, unit)

    assert "# from ollama" in fixed
    assert tokens == 0
    assert cost == 0.0


@pytest.mark.asyncio
async def test_fix_claude_batch_falls_back_to_deterministic_when_ollama_also_fails():
    """Double fallback: router dies, Ollama dies, deterministic saves the day."""
    p = _pipeline()
    unit = WorkUnit(id="B1-0", file_path="src/x.py", app="", issues=[])
    original = "x = 1"

    mock_router = MagicMock()
    mock_router.chat = AsyncMock(side_effect=RuntimeError("no cloud"))

    async def fake_det(code, u):
        return code, 0

    with patch("app.llm.router.get_router", return_value=mock_router), \
         patch.object(p, "_fix_ollama", new=AsyncMock(side_effect=RuntimeError("no ollama"))), \
         patch.object(p, "_fix_deterministic", new=AsyncMock(side_effect=fake_det)):
        fixed, count, tokens, cost = await p._fix_claude_batch(original, unit)

    assert fixed == original
    assert count == 0
    assert tokens == 0
    assert cost == 0.0


# ---------- Router agent map ----------

def test_refactor_fixer_agent_is_claude_only():
    """Sanity: the new virtual agent skips Ollama/Groq in the router chain."""
    from app.llm.router import _CLAUDE_ONLY_AGENTS
    assert "RefactorFixerAgent" in _CLAUDE_ONLY_AGENTS
    assert "ComplianceAgent" in _CLAUDE_ONLY_AGENTS  # preserved from before
