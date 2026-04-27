"""Agent-tool egress audit (A-05, 2026-04-27).

Every call to a content-egressing agent tool — `read_file`,
`write_file`, `list_dir`, `run_code`, `web_scrape` — is wrapped
through `audited(tool_name)` which emits a structured log line
covering: tool, caller agent context (where available), arg keys
and their sizes, result size, success/failure, latency.

What this is NOT
================
- NOT a content DLP. The audit logs DO NOT contain the actual
  content read/scraped/written/executed; only metadata (lengths,
  arg keys, exit codes, error class names). This is intentional:
  audit logs that mirror the egress are themselves a leak surface.
- NOT a real-time block. The audit is observational. Combined with
  log aggregation + alerting it gives ops visibility into what
  the platform's agents are pulling into LLM context, but the
  policy decision (refuse vs allow) lives in the tool itself
  (e.g. C-3 SSRF allowlist, C-4 ALLOW_CODE_EXEC flag).

Storage
=======
For now, audit events are emitted via the standard `logging` chain
under the `nexusforge.tool_audit` logger. Operators with Sentry /
CloudWatch / OpenTelemetry already capture stdout, so no new
sink is required. A future commit can add a Redis stream or a
dedicated `tool_audit_events` table when retention / queryability
become operational requirements.

Privacy
=======
- File paths are recorded as their basename only (not full path) +
  byte size. Avoids leaking directory structure into the log.
- URL hostnames are recorded; the path/query is hashed. Lets ops
  spot exfil patterns ("agent X scraped 200 distinct hosts in 1
  minute") without storing the URLs themselves.
- `run_code` snippets are NOT logged — only `len(code)` and the
  exit code. The blocklist scan reason (if rejected) is logged.
- Error classes are recorded by name only (`type(exc).__name__`),
  matching the F-prior `str(exc)` cleanup pattern.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import logging
import time
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

logger = logging.getLogger("nexusforge.tool_audit")


def _summarize_arg(name: str, value: Any) -> dict[str, Any]:
    """Reduce a tool argument to non-sensitive metadata."""
    if value is None:
        return {"name": name, "is_none": True}
    if isinstance(value, (int, float, bool)):
        return {"name": name, "type": type(value).__name__, "value": value}
    if isinstance(value, str):
        # Special-case the typical content-bearing arg names.
        if name in ("path", "file_path", "filename"):
            from pathlib import Path
            return {
                "name": name,
                "type": "path",
                "basename": Path(value).name,
                "len": len(value),
            }
        if name in ("url",):
            try:
                parsed = urlparse(value)
                return {
                    "name": name,
                    "type": "url",
                    "host": (parsed.hostname or "").lower(),
                    "path_hash": hashlib.sha256(
                        (parsed.path + parsed.query).encode()
                    ).hexdigest()[:12],
                }
            except Exception:
                return {"name": name, "type": "url", "host": "?"}
        if name in ("code",):
            return {"name": name, "type": "code", "len": len(value)}
        if name in ("content",):
            return {"name": name, "type": "content", "len": len(value)}
        # Generic string: just report length so we don't leak prompts.
        return {"name": name, "type": "str", "len": len(value)}
    if isinstance(value, (list, tuple)):
        return {"name": name, "type": "list", "len": len(value)}
    if isinstance(value, dict):
        return {"name": name, "type": "dict", "keys": sorted(value.keys())}
    return {"name": name, "type": type(value).__name__}


def _summarize_result(result: Any) -> dict[str, Any]:
    """Reduce a tool result to non-sensitive metadata.

    Tools in `app.agents.capabilities` return dicts with shape like
    `{stdout, stderr, exit_code}` or `{error: str}` or
    `{content, source, status}`. We probe for known keys without
    surfacing their values.
    """
    if not isinstance(result, dict):
        return {"shape": type(result).__name__}

    summary: dict[str, Any] = {}
    if "error" in result:
        # type(exc).__name__-style errors are already non-sensitive,
        # but full strings could leak details. Truncate aggressively.
        err = result["error"]
        summary["error"] = err[:80] if isinstance(err, str) else type(err).__name__
        return summary
    if "exit_code" in result:
        summary["exit_code"] = result["exit_code"]
    if "stdout" in result:
        summary["stdout_len"] = len(str(result["stdout"]))
    if "stderr" in result:
        summary["stderr_len"] = len(str(result["stderr"]))
    if "content" in result:
        summary["content_len"] = len(str(result["content"]))
    if "size" in result:
        summary["size"] = result["size"]
    if "status" in result:
        summary["status"] = result["status"]
    if "source" in result:
        summary["source"] = result["source"]
    if "entries" in result and isinstance(result["entries"], list):
        summary["entries"] = len(result["entries"])
    return summary


def audited(tool_name: str) -> Callable:
    """Decorator: wrap an async tool call with an egress-audit log.

    Usage:
        @audited("read_file")
        async def read_file(path: str, max_bytes: int = 50_000) -> dict:
            ...

    The decorator preserves the wrapped function's signature so
    callers are unaffected. The audit log line is emitted at INFO
    level on success, WARNING on result containing `error`. Latency
    is measured in milliseconds.
    """
    def deco(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        # Cache the parameter list so we can map positional args to
        # their declared names — needed for the path/url/code/content
        # special-case summarization in `_summarize_arg`.
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            t0 = time.perf_counter()
            arg_summaries: list[dict[str, Any]] = []
            # Recover declared parameter names for positional args.
            for i, value in enumerate(args):
                name = param_names[i] if i < len(param_names) else f"arg{i}"
                arg_summaries.append(_summarize_arg(name, value))
            for name, value in kwargs.items():
                arg_summaries.append(_summarize_arg(name, value))

            outcome = "ok"
            result: Any = None
            try:
                result = await fn(*args, **kwargs)
                if isinstance(result, dict) and "error" in result:
                    outcome = "tool_error"
                return result
            except Exception as exc:
                outcome = "exception"
                result = {"error": type(exc).__name__}
                raise
            finally:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                event = {
                    "tool": tool_name,
                    "outcome": outcome,
                    "elapsed_ms": elapsed_ms,
                    "args": arg_summaries,
                    "result": _summarize_result(result),
                }
                if outcome == "ok":
                    logger.info("tool_audit %s", event)
                else:
                    logger.warning("tool_audit %s", event)

        return wrapper
    return deco
