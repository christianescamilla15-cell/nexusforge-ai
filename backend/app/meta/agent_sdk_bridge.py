"""Claude Agent SDK Bridge — integrates Claude Agent SDK into NexusForge.

Uses the Agent SDK for complex tasks that exceed local LLM capabilities.
Falls back gracefully if SDK is not installed or API key not configured.

2026 Features:
- Built-in tools (Read, Edit, Bash, Glob, Grep, WebSearch)
- Session persistence (resume across queries)
- Custom subagents with specialized prompts
- Hooks for audit trails (PreToolUse, PostToolUse)
- Permission modes (acceptEdits, dontAsk)
- Effort levels (low/medium/high/max)
- MCP server integration
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# Check if Agent SDK is available
_SDK_AVAILABLE = False
_SDK_VERSION = "unknown"
_SDK_SUPPORTS_MEMORY = False  # set by probe below
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
    _SDK_AVAILABLE = True
    try:
        import claude_agent_sdk
        _SDK_VERSION = getattr(claude_agent_sdk, "__version__", "installed")
    except Exception:
        _SDK_VERSION = "installed"

    # Phase 4 — probe whether the installed SDK version supports the
    # ``memory`` kwarg on AgentDefinition. Older pins (<0.1.x) do not.
    # We probe once at import time rather than try/except on every
    # construction. If probe fails, we silently fall back to the no-
    # memory construction path so production stays green on old SDKs.
    try:
        _probe = AgentDefinition(
            description="probe",
            prompt="probe",
            tools=["Read"],
            memory="project",
        )
        _SDK_SUPPORTS_MEMORY = True
        del _probe
    except TypeError:
        # SDK rejects memory kwarg — stay on legacy construction
        _SDK_SUPPORTS_MEMORY = False
    except Exception:
        # Any other error during probe: treat as unsupported to be safe
        _SDK_SUPPORTS_MEMORY = False
except ImportError:
    logger.info("Claude Agent SDK not installed — SDK bridge disabled. Install with: pip install claude-agent-sdk")


# Redis key template for Phase 4 session persistence. Scoped by
# user_id AND agent_name so a single user can run parallel sessions
# against different subagent contexts without stomping each other.
_SESSION_REDIS_KEY = "nexusforge:sdk:session:{user_id}:{agent_name}"
_SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days — covers ~1 Render redeploy cycle


def _make_agent_definition(*, description: str, prompt: str, tools: list[str]):
    """Construct an AgentDefinition, passing ``memory="project"`` when
    the installed SDK supports it (probed once at import time).

    This keeps the hot path out of try/except. Older SDK versions that
    do not know the ``memory`` kwarg fall through to a plain
    construction so the bridge still works on the pinned baseline.
    """
    if not _SDK_AVAILABLE:
        return None  # pragma: no cover — unreachable when used from _execute
    if _SDK_SUPPORTS_MEMORY:
        return AgentDefinition(
            description=description,
            prompt=prompt,
            tools=tools,
            memory="project",
        )
    return AgentDefinition(
        description=description,
        prompt=prompt,
        tools=tools,
    )


class AgentSDKBridge:
    """Bridge between NexusForge orchestrator and Claude Agent SDK.

    Used for tasks that need:
    - File system access (read/edit code)
    - Web search (research)
    - Multi-step reasoning with tool use
    - Session persistence across queries
    - Sub-agent delegation for specialized tasks
    """

    # NexusForge specialized sub-agents
    NEXUSFORGE_AGENTS = {
        "security-auditor": {
            "description": "OWASP top 10, dependency vulns, secret scanning",
            "prompt": "Audit for SQL injection, XSS, auth flaws, insecure crypto, hardcoded secrets.",
            "tools": ["Read", "Glob", "Grep"],
        },
        "code-reviewer": {
            "description": "Code quality, patterns, performance review",
            "prompt": "Review for best practices, design patterns, performance issues, error handling.",
            "tools": ["Read", "Glob", "Grep"],
        },
        "test-engineer": {
            "description": "Test strategy, coverage analysis, test generation",
            "prompt": "Analyze test coverage, suggest missing tests, generate test cases.",
            "tools": ["Read", "Glob", "Grep", "Bash"],
        },
        "architect": {
            "description": "System design, architecture decisions, scalability",
            "prompt": "Evaluate architecture, suggest improvements, identify bottlenecks.",
            "tools": ["Read", "Glob", "Grep"],
        },
    }

    def __init__(self):
        self._available = _SDK_AVAILABLE and bool(os.environ.get("ANTHROPIC_API_KEY"))
        self._session_id = None
        self._audit_log: list[dict] = []

    @property
    def available(self) -> bool:
        return self._available

    @property
    def version(self) -> str:
        return _SDK_VERSION

    def get_audit_log(self) -> list[dict]:
        """Return recent audit entries (last 100)."""
        return self._audit_log[-100:]

    async def run(
        self,
        prompt: str,
        tools: list[str] | None = None,
        agents: dict[str, dict] | None = None,
        resume_session: bool = False,
        effort: str = "medium",
        permission_mode: str = "dontAsk",
        max_turns: int = 15,
        user_id: str | None = None,
        agent_name: str = "default",
    ) -> dict[str, Any]:
        """Run a query through the Claude Agent SDK.

        Args:
            prompt: The task to perform
            tools: Allowed tools (Read, Edit, Bash, Glob, Grep, WebSearch, etc.)
            agents: Custom subagent definitions {name: {description, prompt, tools}}
            resume_session: Resume previous session context. If user_id
                is provided, the session id is looked up in Redis under
                ``nexusforge:sdk:session:{user_id}:{agent_name}`` rather
                than the in-memory singleton attribute.
            effort: Thinking effort (low, medium, high, max)
            permission_mode: acceptEdits | dontAsk | default
            max_turns: Max agent loop iterations
            user_id: Optional user identifier used for Phase 4 Redis-
                backed session persistence. When present, session ids
                captured during ``_execute`` are written to Redis at the
                end of a successful run.
            agent_name: Namespace within the per-user session keyspace.
                Defaults to ``"default"``. Use one of the subagent keys
                in ``NEXUSFORGE_AGENTS`` (or any custom string) to keep
                parallel sessions separate.
        """
        if not self._available:
            return {
                "result": "Agent SDK not available (install claude-agent-sdk or set ANTHROPIC_API_KEY)",
                "session_id": None,
                "tools_used": [],
                "tokens": 0,
                "cost_usd": 0.0,
                "status": "unavailable",
            }

        # Phase 4 — if caller asked to resume and we have a user scope,
        # look up the durable session id from Redis and seed
        # self._session_id so _execute will pass it through resume=.
        if resume_session and user_id:
            persisted = await self._load_session(user_id, agent_name)
            if persisted:
                self._session_id = persisted

        try:
            start = time.monotonic()
            result = await self._execute(prompt, tools, agents, resume_session, effort, permission_mode, max_turns)
            result["duration_ms"] = int((time.monotonic() - start) * 1000)

            # Phase 4 — persist the (possibly new) session id so the
            # next call can resume it even after a process restart.
            if user_id and result.get("session_id"):
                await self._save_session(user_id, agent_name, result["session_id"])
                result["session_persisted"] = True
            self._audit_log.append({
                "timestamp": time.time(),
                "prompt": prompt[:200],
                "status": result["status"],
                "tokens": result["tokens"],
                "tools_used": result["tools_used"],
                "duration_ms": result["duration_ms"],
            })
            return result
        except Exception as e:
            logger.error("Agent SDK execution failed: %s", e)
            return {
                "result": f"Agent SDK error: {e}",
                "session_id": self._session_id,
                "tools_used": [],
                "tokens": 0,
                "cost_usd": 0.0,
                "status": "error",
            }

    async def _execute(
        self, prompt, tools, agents, resume_session, effort, permission_mode, max_turns
    ) -> dict[str, Any]:
        """Internal execution using the SDK."""
        options_kwargs = {
            "permission_mode": permission_mode,
        }

        # Tools
        if tools:
            options_kwargs["allowed_tools"] = tools
        else:
            options_kwargs["allowed_tools"] = ["Read", "Glob", "Grep"]

        # Session resume
        if resume_session and self._session_id:
            options_kwargs["resume"] = self._session_id

        # Sub-agents — merge NexusForge defaults with custom agents.
        # Phase 4: when the installed SDK supports it, pass
        # memory="project" on each AgentDefinition so the subagent
        # can retain context across invocations within a project
        # scope. Falls back to the no-memory construction if the SDK
        # is too old (probed once at import time).
        sdk_agents = {}
        for name, config in self.NEXUSFORGE_AGENTS.items():
            sdk_agents[name] = _make_agent_definition(
                description=config["description"],
                prompt=config["prompt"],
                tools=config["tools"],
            )
        if agents:
            for name, config in agents.items():
                sdk_agents[name] = _make_agent_definition(
                    description=config.get("description", ""),
                    prompt=config.get("prompt", ""),
                    tools=config.get("tools", ["Read", "Glob", "Grep"]),
                )
        options_kwargs["agents"] = sdk_agents

        options = ClaudeAgentOptions(**options_kwargs)

        result_text = ""
        tools_used = []
        total_input = 0
        total_output = 0

        async for message in query(prompt=prompt, options=options):
            # Capture session ID
            if hasattr(message, "subtype") and message.subtype == "init":
                self._session_id = getattr(message, "data", {}).get("session_id")

            # Capture result
            if hasattr(message, "result"):
                result_text = message.result

            # Track tool usage
            if hasattr(message, "tool_name"):
                tools_used.append(message.tool_name)

            # Track tokens
            if hasattr(message, "usage"):
                total_input += getattr(message.usage, "input_tokens", 0)
                total_output += getattr(message.usage, "output_tokens", 0)

        total_tokens = total_input + total_output
        # Estimate cost (Sonnet 4.6 default: $3/$15 per MTok)
        cost_usd = (total_input / 1_000_000) * 3.0 + (total_output / 1_000_000) * 15.0

        return {
            "result": result_text,
            "session_id": self._session_id,
            "tools_used": list(set(tools_used)),
            "tokens": total_tokens,
            "tokens_input": total_input,
            "tokens_output": total_output,
            "cost_usd": round(cost_usd, 4),
            "status": "success",
        }

    # ── Phase 4: Redis-backed session persistence ──────────────────────────
    #
    # Session ids issued by the SDK normally live in ``self._session_id``
    # as an in-memory attribute. On Render that dies with the process —
    # every redeploy loses all sessions. Persisting the id to Redis lets
    # ``resume()`` pick up where a previous process left off, subject to
    # the Render ephemeral-FS caveat documented in docs/DEPLOYMENT.md:
    # the SDK's own transcript files may be gone even when the id is
    # still valid, in which case the resume degrades to a fresh start.

    async def _load_session(self, user_id: str, agent_name: str) -> str | None:
        """Fetch a previously persisted session id from Redis.

        Returns None if Redis is unavailable, the key does not exist,
        or the stored value is not a string. Errors are swallowed —
        this is a best-effort enhancement and must never crash
        ``run()``.
        """
        try:
            from app.db.client import get_redis
            redis = await get_redis()
            if redis is None:
                return None
            key = _SESSION_REDIS_KEY.format(user_id=user_id, agent_name=agent_name)
            value = await redis.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="ignore")
            return str(value)
        except Exception as exc:
            logger.debug("SDK bridge: failed to load session for %s/%s: %s", user_id, agent_name, exc)
            return None

    async def _save_session(self, user_id: str, agent_name: str, session_id: str) -> None:
        """Persist a session id to Redis with a 7-day TTL. Best effort."""
        try:
            from app.db.client import get_redis
            redis = await get_redis()
            if redis is None:
                return
            key = _SESSION_REDIS_KEY.format(user_id=user_id, agent_name=agent_name)
            await redis.set(key, session_id, ex=_SESSION_TTL_SECONDS)
        except Exception as exc:
            logger.debug("SDK bridge: failed to save session for %s/%s: %s", user_id, agent_name, exc)

    async def resume(
        self,
        prompt: str,
        user_id: str,
        agent_name: str = "default",
        tools: list[str] | None = None,
        agents: dict[str, dict] | None = None,
        effort: str = "medium",
        permission_mode: str = "dontAsk",
        max_turns: int = 15,
    ) -> dict[str, Any]:
        """Resume a previously persisted SDK session for this user/agent.

        Thin wrapper over ``run(..., resume_session=True)`` that makes
        the intent explicit and keeps the caller path free of kwarg
        noise. If no session is persisted, the SDK will start a new
        one and ``run`` will persist it on the way out.
        """
        return await self.run(
            prompt=prompt,
            tools=tools,
            agents=agents,
            resume_session=True,
            effort=effort,
            permission_mode=permission_mode,
            max_turns=max_turns,
            user_id=user_id,
            agent_name=agent_name,
        )

    # ── Convenience methods ─────────────────────────────────────────────────

    async def code_review(self, file_path: str) -> dict:
        """Thorough code review with security sub-agent."""
        return await self.run(
            prompt=f"Review {file_path} for bugs, security issues, and best practices. Be concise.",
            tools=["Read", "Glob", "Grep", "Agent"],
        )

    async def research(self, topic: str) -> dict:
        """Research a topic with web search."""
        return await self.run(
            prompt=f"Research: {topic}. Provide a concise summary with key findings.",
            tools=["WebSearch", "WebFetch", "Read"],
        )

    async def fix_bug(self, description: str) -> dict:
        """Find and fix a bug."""
        return await self.run(
            prompt=f"Find and fix this bug: {description}. Read the relevant files, identify the root cause, and apply the minimal fix.",
            tools=["Read", "Glob", "Grep", "Edit"],
            permission_mode="acceptEdits",
        )

    async def analyze_codebase(self, focus: str = "") -> dict:
        """Full codebase analysis with multiple sub-agents."""
        prompt = "Analyze this codebase thoroughly using sub-agents for different perspectives."
        if focus:
            prompt += f" Focus on: {focus}"
        return await self.run(
            prompt=prompt,
            tools=["Read", "Glob", "Grep", "Agent"],
            effort="high",
        )


# ── Singleton ────────────────────────────────────────────────────────────────

_bridge: AgentSDKBridge | None = None


def get_sdk_bridge() -> AgentSDKBridge:
    global _bridge
    if _bridge is None:
        _bridge = AgentSDKBridge()
    return _bridge
