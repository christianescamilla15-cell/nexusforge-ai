"""Claude Agent SDK Bridge — integrates Claude Agent SDK into the meta-orchestrator.

Uses the Agent SDK for complex tasks that exceed local LLM capabilities.
Falls back gracefully if SDK is not installed or API key not configured.

The SDK provides:
- Built-in tools (Read, Edit, Bash, Glob, Grep, WebSearch)
- Session persistence (resume across queries)
- Custom subagents with specialized prompts
- Hooks for audit trails
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Check if Agent SDK is available
_SDK_AVAILABLE = False
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
    _SDK_AVAILABLE = True
except ImportError:
    logger.info("Claude Agent SDK not installed — SDK bridge disabled. Install with: pip install claude-agent-sdk")


class AgentSDKBridge:
    """Bridge between NexusForge meta-orchestrator and Claude Agent SDK.

    Used for tasks that need:
    - File system access (read/edit code)
    - Web search (research)
    - Multi-step reasoning with tool use
    - Session persistence across queries
    """

    def __init__(self):
        self._available = _SDK_AVAILABLE and bool(os.environ.get("ANTHROPIC_API_KEY"))
        self._session_id = None

    @property
    def available(self) -> bool:
        return self._available

    async def run(
        self,
        prompt: str,
        tools: list[str] | None = None,
        agents: dict[str, dict] | None = None,
        resume_session: bool = False,
        max_turns: int = 10,
    ) -> dict[str, Any]:
        """Run a query through the Claude Agent SDK.

        Args:
            prompt: The task to perform
            tools: List of allowed tools (Read, Edit, Bash, Glob, Grep, WebSearch, etc.)
            agents: Custom subagent definitions {name: {description, prompt, tools}}
            resume_session: Whether to resume the previous session
            max_turns: Maximum agent loop iterations

        Returns:
            {result: str, session_id: str, tools_used: list, tokens: int}
        """
        if not self._available:
            return {
                "result": "Agent SDK not available (install claude-agent-sdk or set ANTHROPIC_API_KEY)",
                "session_id": None,
                "tools_used": [],
                "tokens": 0,
                "status": "unavailable",
            }

        try:
            return await self._execute(prompt, tools, agents, resume_session, max_turns)
        except Exception as e:
            logger.error("Agent SDK execution failed: %s", e)
            return {
                "result": f"Agent SDK error: {e}",
                "session_id": self._session_id,
                "tools_used": [],
                "tokens": 0,
                "status": "error",
            }

    async def _execute(
        self, prompt, tools, agents, resume_session, max_turns
    ) -> dict[str, Any]:
        """Internal execution using the SDK."""
        options_kwargs = {}

        if tools:
            options_kwargs["allowed_tools"] = tools
        else:
            options_kwargs["allowed_tools"] = ["Read", "Glob", "Grep"]

        if resume_session and self._session_id:
            options_kwargs["resume"] = self._session_id

        if agents:
            sdk_agents = {}
            for name, config in agents.items():
                sdk_agents[name] = AgentDefinition(
                    description=config.get("description", ""),
                    prompt=config.get("prompt", ""),
                    tools=config.get("tools", ["Read", "Glob", "Grep"]),
                )
            options_kwargs["agents"] = sdk_agents

        options = ClaudeAgentOptions(**options_kwargs)

        result_text = ""
        tools_used = []
        total_tokens = 0

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
                total_tokens += getattr(message.usage, "input_tokens", 0)
                total_tokens += getattr(message.usage, "output_tokens", 0)

        return {
            "result": result_text,
            "session_id": self._session_id,
            "tools_used": list(set(tools_used)),
            "tokens": total_tokens,
            "status": "success",
        }

    async def code_review(self, file_path: str) -> dict:
        """Use Agent SDK to perform a thorough code review."""
        return await self.run(
            prompt=f"Review {file_path} for bugs, security issues, and best practices. Be concise.",
            tools=["Read", "Glob", "Grep"],
            agents={
                "security-reviewer": {
                    "description": "Security vulnerability scanner",
                    "prompt": "Check for OWASP top 10 vulnerabilities, hardcoded secrets, and injection risks.",
                    "tools": ["Read", "Grep"],
                },
            },
        )

    async def research(self, topic: str) -> dict:
        """Use Agent SDK to research a topic with web search."""
        return await self.run(
            prompt=f"Research: {topic}. Provide a concise summary with key findings.",
            tools=["WebSearch", "WebFetch", "Read"],
        )

    async def fix_bug(self, description: str) -> dict:
        """Use Agent SDK to find and fix a bug."""
        return await self.run(
            prompt=f"Find and fix this bug: {description}. Read the relevant files, identify the root cause, and suggest the minimal fix.",
            tools=["Read", "Glob", "Grep", "Edit"],
        )


# ── Singleton ────────────────────────────────────────────────────────────────

_bridge: AgentSDKBridge | None = None


def get_sdk_bridge() -> AgentSDKBridge:
    global _bridge
    if _bridge is None:
        _bridge = AgentSDKBridge()
    return _bridge
