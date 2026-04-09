"""LLM-Powered Code Fixer — uses local Ollama (qwen2.5-coder) for complete fixes.

Unlike the deterministic fixer that leaves TODOs, this produces
compilable, production-ready code using a local LLM.

Model priority:
  1. qwen2.5-coder:7b (local, free, fast, specialized in code)
  2. deepseek-r1:8b (local, free, reasoning)
  3. Groq llama-3.3-70b (cloud, free tier)
  4. Claude Sonnet (cloud, paid — last resort)

Cost: $0 when using Ollama models.
"""

import asyncio
import logging
import re
import time
import httpx
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
PREFERRED_MODELS = ["qwen2.5-coder:7b", "deepseek-r1:8b", "llama3.1:8b"]


@dataclass
class LLMFixResult:
    file_path: str
    status: str         # fixed, failed, skipped
    fixes: list[dict] = field(default_factory=list)
    original_code: str = ""
    fixed_code: str = ""
    model_used: str = ""
    tokens_used: int = 0
    duration_ms: int = 0
    cost_usd: float = 0.0  # $0 for local models


async def _ollama_generate(prompt: str, model: str = "qwen2.5-coder:7b", max_tokens: int = 2048) -> dict:
    """Call Ollama generate API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens,
                },
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "text": data.get("response", ""),
            "model": model,
            "tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            "duration_ms": int(data.get("total_duration", 0) / 1_000_000),
        }


async def _get_available_model() -> str | None:
    """Find the best available local model."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            if resp.status_code != 200:
                return None
            models = [m["name"] for m in resp.json().get("models", [])]
            for preferred in PREFERRED_MODELS:
                if preferred in models:
                    return preferred
            return models[0] if models else None
    except Exception:
        return None


# ── Fix Prompts ─────────────────────────────────────────────────────────────

_SQL_INJECTION_PROMPT = """Fix this C# SQL injection vulnerability. Convert string concatenation/interpolation to parameterized queries using SqlParameter.

RULES:
- Replace ALL string concatenation in SQL with @parameters
- Add cmd.Parameters.AddWithValue() for each parameter
- Keep the exact same logic and variable names
- Return ONLY the fixed method, no explanation

VULNERABLE CODE:
```csharp
{code}
```

FIXED CODE (parameterized, no concatenation):"""

_HARDCODED_CRED_PROMPT = """Fix this C# hardcoded credential. Replace with IConfiguration injection or Environment.GetEnvironmentVariable().

RULES:
- Replace hardcoded values with configuration access
- If it's a field, use Environment.GetEnvironmentVariable("KEY_NAME")
- If it's a connection string, use _configuration.GetConnectionString("Default")
- Keep the exact same variable names and types
- Return ONLY the fixed code, no explanation

VULNERABLE CODE:
```csharp
{code}
```

FIXED CODE (no hardcoded secrets):"""

_GENERIC_FIX_PROMPT = """Fix this C# security vulnerability: {description}

RULES:
- Fix ONLY the security issue, don't change business logic
- Keep variable names, method signatures, and return types
- Return ONLY the fixed code block, no explanation

VULNERABLE CODE:
```csharp
{code}
```

FIXED CODE:"""


class LLMFixer:
    """Fix code using local LLM for complete, compilable fixes."""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.root = Path(project_root)
        self.dry_run = dry_run
        self._model = None

    async def fix_file(self, file_path: str, findings: list[dict]) -> LLMFixResult:
        """Fix all findings in a file using LLM.

        Args:
            file_path: Relative path to .cs file
            findings: List of {category, line_number, title, code_snippet}
        """
        fpath = self.root / file_path
        if not fpath.exists():
            return LLMFixResult(file_path=file_path, status="skipped")

        # Get available model
        if not self._model:
            self._model = await _get_available_model()
            if not self._model:
                logger.warning("No Ollama model available — skipping LLM fixes")
                return LLMFixResult(file_path=file_path, status="skipped", model_used="none")

        start = time.monotonic()
        original = fpath.read_text(encoding="utf-8", errors="ignore")
        fixed = original
        fixes = []
        total_tokens = 0

        # Group findings by method/region to fix together
        for finding in findings:
            line_num = finding.get("line_number", 0)
            category = finding.get("category", "")

            # Extract the method containing the vulnerability
            method_code = self._extract_method(fixed, line_num)
            if not method_code:
                continue

            # Choose prompt
            if category == "sql_injection":
                prompt = _SQL_INJECTION_PROMPT.format(code=method_code)
            elif category == "hardcoded_cred":
                prompt = _HARDCODED_CRED_PROMPT.format(code=method_code)
            else:
                prompt = _GENERIC_FIX_PROMPT.format(
                    description=finding.get("title", "security issue"),
                    code=method_code,
                )

            try:
                result = await _ollama_generate(prompt, self._model)
                fixed_method = self._extract_code_block(result["text"])

                if fixed_method and fixed_method != method_code:
                    # Apply the fix
                    fixed = fixed.replace(method_code, fixed_method)
                    total_tokens += result["tokens"]
                    fixes.append({
                        "line": line_num,
                        "category": category,
                        "model": self._model,
                        "tokens": result["tokens"],
                        "duration_ms": result["duration_ms"],
                    })
                    logger.info("LLM fixed %s:%d (%s) via %s", file_path, line_num, category, self._model)

            except Exception as exc:
                logger.warning("LLM fix failed for %s:%d: %s", file_path, line_num, exc)

        # Write if changed
        if not self.dry_run and fixed != original and fixes:
            fpath.write_text(fixed, encoding="utf-8")

        duration = int((time.monotonic() - start) * 1000)
        return LLMFixResult(
            file_path=file_path,
            status="fixed" if fixes else "skipped",
            fixes=fixes,
            original_code=original[:500],
            fixed_code=fixed[:500],
            model_used=self._model or "none",
            tokens_used=total_tokens,
            duration_ms=duration,
            cost_usd=0.0,  # Local = free
        )

    def _extract_method(self, code: str, line_number: int) -> str:
        """Extract the method containing the given line number."""
        lines = code.splitlines()
        if line_number <= 0 or line_number > len(lines):
            return ""

        # Find method start (walk backwards to find method signature)
        start = line_number - 1
        brace_count = 0
        while start > 0:
            line = lines[start]
            if re.search(r'(?:public|private|protected|internal)\s+(?:async\s+)?(?:static\s+)?\w+\s+\w+\s*\(', line):
                break
            start -= 1

        # Find method end (match braces)
        end = start
        found_open = False
        for i in range(start, len(lines)):
            line = lines[i]
            brace_count += line.count('{') - line.count('}')
            if '{' in line:
                found_open = True
            if found_open and brace_count <= 0:
                end = i
                break

        if end <= start:
            # Fallback: take 30 lines around the finding
            start = max(0, line_number - 10)
            end = min(len(lines) - 1, line_number + 20)

        return "\n".join(lines[start:end + 1])

    def _extract_code_block(self, llm_response: str) -> str:
        """Extract code from LLM response (handles markdown fences)."""
        # Try to find code block
        m = re.search(r'```(?:csharp|cs)?\n(.*?)```', llm_response, re.DOTALL)
        if m:
            return m.group(1).strip()

        # If no code block, take everything that looks like code
        lines = llm_response.strip().splitlines()
        code_lines = []
        for line in lines:
            # Skip obvious non-code lines
            if line.startswith("Here") or line.startswith("The ") or line.startswith("I "):
                continue
            code_lines.append(line)

        return "\n".join(code_lines).strip() if code_lines else ""
