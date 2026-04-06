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
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ── Tool implementations ─────────────────────────────────────────────────────

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


async def write_file(path: str, content: str) -> dict:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p.resolve()), "written_bytes": len(content.encode())}
    except Exception as exc:
        return {"error": str(exc)}


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


async def run_code(code: str, language: str = "python", timeout: int = 10) -> dict:
    """Execute a code snippet in a subprocess sandbox."""
    if language != "python":
        return {"error": f"Only Python is supported, got: {language}"}
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
        return {"error": str(exc)}


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
