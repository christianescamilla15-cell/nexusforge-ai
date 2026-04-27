"""AgentCapabilities — real tool powers per agent.

Each agent declares what it can do beyond LLM calls.
Tools are executed locally using actual system resources.

Capability registry:
    RepairAgent      → read_file, list_dir, run_code
    ResearcherAgent  → web_scrape, web_search
    KnowledgeAgent   → rag_query, read_file
    ExtractorAgent   → read_file, parse_pdf
    NormalizerAgent  → read_file, write_file
    MonitorAgent     → read_file, list_dir

A-05 (2026-04-27): every content-egress tool below is wrapped
with `@audited(...)` from `app.agents.tool_audit`. Each call emits
a structured log line covering tool name, arg metadata (sizes,
basenames, hostnames — never content), result size, latency, and
outcome. Search the `nexusforge.tool_audit` logger to see the
egress feed.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

import httpx

from app.agents.tool_audit import audited

logger = logging.getLogger(__name__)

# ── Tool implementations ─────────────────────────────────────────────────────

@audited("read_file")
async def read_file(path: str, max_bytes: int = 50_000) -> dict:
    """Read a file from the local filesystem."""
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_bytes:
            content = content[:max_bytes] + f"\n... [truncated at {max_bytes} bytes]"
        return {"path": str(p.resolve()), "content": content, "size": p.stat().st_size}
    except Exception as exc:
        return {"error": str(exc)}


@audited("write_file")
async def write_file(path: str, content: str) -> dict:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p.resolve()), "written_bytes": len(content.encode())}
    except Exception as exc:
        return {"error": str(exc)}


@audited("list_dir")
async def list_dir(path: str) -> dict:
    """List files and directories at path."""
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        entries = [
            {"name": e.name, "type": "dir" if e.is_dir() else "file", "size": e.stat().st_size if e.is_file() else None}
            for e in sorted(p.iterdir())
        ]
        return {"path": str(p.resolve()), "entries": entries, "count": len(entries)}
    except Exception as exc:
        return {"error": str(exc)}


# C-4 (2026-04-25): names/calls that, if present in submitted code,
# refuse the whole snippet. Not a true sandbox — a real sandbox needs
# nsjail/firejail/seccomp at the OS level. This blocklist raises the
# cost of the obvious exfiltration patterns (env-var read, network
# call, subprocess spawn, file system access outside CWD) and forces
# any future expansion through code review.
_RUN_CODE_BLOCKLIST = frozenset({
    # Obvious exfil targets
    "os.environ", "os.getenv", "environ",
    # Process spawning
    "subprocess", "popen", "system",
    # Network
    "socket", "urllib", "httpx", "requests", "aiohttp", "smtplib",
    # File-system escape
    "open(", "pathlib", "shutil",
    # Reflection / dynamic loading
    "__import__", "importlib", "ctypes",
    # Eval / exec
    "exec(", "eval(", "compile(",
})


def _run_code_scan(code: str) -> str | None:
    """Return a rejection reason if the snippet looks dangerous, else None."""
    lowered = code.lower()
    for token in _RUN_CODE_BLOCKLIST:
        if token in lowered:
            return f"Disallowed token: {token!r}"
    return None


@audited("run_code")
async def run_code(code: str, language: str = "python", timeout: int = 10) -> dict:
    """Execute a code snippet in a subprocess.

    C-4 hardening (2026-04-25):
      1. Disabled by default. Set `ALLOW_CODE_EXEC=true` in env to
         enable. Production deploys must keep this off until a real
         sandbox (nsjail / firejail / gVisor) is in place.
      2. AST-style blocklist scan rejects obvious exfiltration
         patterns (env var reads, network libs, subprocess spawn,
         filesystem escape, eval/exec/import).
      3. Subprocess inherits a SCRUBBED env that omits all NexusForge
         secrets — even if the blocklist is bypassed, JWT_SECRET /
         STRIPE_SECRET_KEY / ANTHROPIC_API_KEY / DATABASE_URL are
         not visible inside the snippet's `os.environ`.

    None of the above replaces a real sandbox; treat this tool as
    "enabled developer-debug only" until C-4-followup ships nsjail.
    """
    if language != "python":
        return {"error": f"Only Python is supported, got: {language}"}

    # Feature flag — default off.
    if os.environ.get("ALLOW_CODE_EXEC", "").lower() not in ("true", "1", "yes"):
        return {
            "error": (
                "run_code is disabled by default. "
                "Set ALLOW_CODE_EXEC=true to enable (developer-debug only)."
            ),
        }

    # Static blocklist scan — fail fast on obvious bad patterns.
    rejection = _run_code_scan(code)
    if rejection:
        logger.warning("run_code rejected snippet: %s", rejection)
        return {"error": f"Code rejected: {rejection}"}

    # Scrub the env so the snippet cannot read NexusForge secrets
    # via os.environ even if it imports `os` somehow.
    safe_env_keys = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ"}
    clean_env = {k: v for k, v in os.environ.items() if k in safe_env_keys}

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=clean_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "stdout": stdout.decode()[:5000],
            "stderr": stderr.decode()[:2000],
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"error": f"Code execution timed out after {timeout}s"}
    except Exception as exc:
        return {"error": type(exc).__name__}


@audited("web_scrape")
async def web_scrape(url: str) -> dict:
    """Scrape a URL using Crawl4AI or httpx fallback."""
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {"url": url, "content": result.markdown[:10_000], "source": "crawl4ai"}
    except ImportError:
        pass
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            return {"url": url, "content": resp.text[:10_000], "source": "httpx", "status": resp.status_code}
    except Exception as exc:
        return {"error": str(exc)}


async def rag_query(query: str, collection: str = "nexusforge") -> dict:
    """Query the RAG vector store for relevant context."""
    try:
        from app.rag.retriever import get_retriever
        retriever = get_retriever(collection)
        docs = await retriever.retrieve(query, top_k=5)
        return {
            "query": query,
            "results": [{"content": d.content, "score": d.score, "source": d.source} for d in docs],
        }
    except Exception as exc:
        return {"error": str(exc)}


# ── Capability registry ──────────────────────────────────────────────────────

_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_code": run_code,
    "web_scrape": web_scrape,
    "rag_query": rag_query,
}

# Map agent name → list of allowed tools
AGENT_CAPABILITIES: dict[str, list[str]] = {
    "RepairAgent":      ["read_file", "list_dir", "run_code"],
    "ResearcherAgent":  ["web_scrape"],
    "ScraperAgent":     ["web_scrape"],
    "KnowledgeAgent":   ["rag_query", "read_file"],
    "ExtractorAgent":   ["read_file"],
    "NormalizerAgent":  ["read_file", "write_file"],
    "MonitorAgent":     ["read_file", "list_dir"],
    "EnricherAgent":    ["web_scrape"],
    "AnalyzerAgent":    ["read_file", "rag_query"],
    "ValidatorAgent":   ["read_file", "run_code"],
}


class AgentCapabilities:
    """Provides tool access to an agent based on its capability declarations."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._allowed = set(AGENT_CAPABILITIES.get(agent_name, []))

    def can(self, tool: str) -> bool:
        return tool in self._allowed

    async def use(self, tool: str, **kwargs) -> dict:
        """Execute a tool if the agent is authorized to use it."""
        if tool not in self._allowed:
            return {"error": f"Agent '{self.agent_name}' is not authorized to use tool '{tool}'"}
        fn = _TOOLS.get(tool)
        if fn is None:
            return {"error": f"Tool '{tool}' does not exist"}
        logger.info("Agent '%s' using tool '%s' with args %s", self.agent_name, tool, list(kwargs.keys()))
        return await fn(**kwargs)

    @property
    def available_tools(self) -> list[str]:
        return sorted(self._allowed)
