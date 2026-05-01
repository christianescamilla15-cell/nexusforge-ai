"""Conversational spec extractor for the Platform Synthesizer.

The goal of this module: take a user's free-form description of
what they want to build ("a Python dashboard for tracking my
inventory with Slack alerts"), have Claude extract structured
slots into a `PlatformSpec`, AND produce a natural follow-up
reply that asks for the next missing piece.

Why both in one call: the UX is a chat panel on the left and a
template-suggestion panel on the right that updates LIVE as the
user types. Two round-trips per turn would feel laggy. One call
that returns both keeps the panel responsive.

Robustness: the parser handles the common LLM failure modes
(model wraps JSON in code fences, model invents fields, model
omits fields). When extraction fails the assistant message still
gets through — the user keeps chatting and we try again on the
next turn.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from .schemas import (
    ChatTurnInput,
    ChatTurnOutput,
    PlatformSpec,
    TemplateMatch,
)
from .templates import list_templates, rank_for_spec

logger = logging.getLogger(__name__)


# ── system prompt ──────────────────────────────────────────────────


def _build_system_prompt(current_spec: Optional[PlatformSpec]) -> str:
    """Compose the system prompt. Embeds the current accumulated
    spec so Claude doesn't repeat questions and only asks about
    missing slots."""

    template_names = [t.name for t in list_templates()]
    current_spec_json = (
        current_spec.model_dump_json(indent=2) if current_spec else "{}"
    )

    return f"""You are the NexusForge Platform Synthesizer assistant.

Your job: help the user describe a project they want to generate
(name, language, framework, features, integrations, auth model).
Each turn, you do TWO things:

1. Reply with a SHORT, friendly chat message — one focused
   follow-up question OR a confirmation. Spanish if the user
   writes in Spanish, English otherwise. Use plain prose, no
   markdown tables, no code blocks.

2. Emit an updated structured spec describing what you've
   inferred so far.

# Available templates (the project will be generated from one of these)

{chr(10).join(f"- {n}" for n in template_names)}

# Current accumulated spec

```json
{current_spec_json}
```

# How to fill the spec

Each slot fills as you learn it. Don't invent values the user
hasn't given you. Slots:

- project_name: short, lowercase, hyphen-separated. If the user
  said "an inventory tracker", suggest "inventory-tracker" but
  ask them to confirm.
- description: one sentence summary.
- language: one of "python", "typescript", "javascript", "go",
  "rust", "ruby", "elixir", "java" (lowercase). NULL if unspecified.
- backend_framework: e.g. "fastapi", "express", "django",
  "rails", "phoenix", "spring".
- frontend_framework: one of "react", "vue", "next", "svelte",
  "none". NULL if unspecified.
- database: one of "postgres", "mysql", "sqlite", "mongo", "none".
- features: array of short capability strings the user mentioned
  ("user auth", "dashboard", "csv export", "ai chat", etc.).
- auth: one of "none", "jwt", "google_oauth", "supabase", "auth0".
- integrations: array of external services named
  ("slack", "stripe", "openai", etc.).
- notes: anything the user said you couldn't fit into a slot.

# Output format — STRICT

Reply with exactly one JSON object, nothing else (no preamble, no
code fences, no trailing text). The JSON has these keys:

{{
  "assistant_message": "<your short chat reply>",
  "spec_updates": {{ /* only fields you learned this turn — OMIT keys you didn't infer */ }}
}}

The frontend MERGES `spec_updates` into the current spec. If the
user contradicts a previous slot ("actually, make it Go not
Python"), include the new value in `spec_updates` to overwrite.

If the spec looks complete enough to build (project_name,
language, backend_framework, frontend_framework, and at least
one of features/auth/integrations all filled), your
assistant_message should suggest "Looks ready — pick a template
on the right and click Build" instead of asking another question.
"""


# ── Claude call ─────────────────────────────────────────────────────


async def _call_claude(system: str, history: list[dict], user_message: str) -> str:
    """Send the chat to Claude (Haiku for cost). Returns raw text.

    History is the prior chat turns in
    [{"role": "user"|"assistant", "content": "..."}] shape — we
    pass them through unchanged so Claude has continuity.
    """
    from app.llm.haiku_provider import HaikuProvider

    provider = HaikuProvider()
    if not provider.is_available():
        # No Anthropic API key — return a degraded fallback that
        # at least doesn't error out the caller.
        logger.warning("HaikuProvider unavailable (no ANTHROPIC_API_KEY)")
        return json.dumps(
            {
                "assistant_message": (
                    "Anthropic API key isn't configured on this deploy, so I can't "
                    "extract structured spec from chat right now. Use the template "
                    "list on the right to pick one directly and we'll build with the "
                    "fields you fill in below."
                ),
                "spec_updates": {},
            }
        )

    messages: list[dict] = [{"role": "system", "content": system}]
    # History last (so user message is most recent).
    for turn in history:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    response = await provider.chat(messages, temperature=0.2, max_tokens=600)
    return response.text


# ── parser ─────────────────────────────────────────────────────────


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Tolerant JSON extractor.

    Handles three failure modes:
      1. Pure JSON → json.loads directly.
      2. JSON inside ```json ... ``` fence → strip fence first.
      3. JSON with trailing/leading prose → grab the first {..}
         block by brace counting.
    """
    text = text.strip()

    # Path 1: try direct parse first (fast happy path).
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Path 2: strip code fence if present.
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Path 3: brace-balance to find the first complete JSON object.
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    raise ValueError("Could not parse JSON from response")


def _merge_spec(current: Optional[PlatformSpec], updates: dict) -> PlatformSpec:
    """Merge LLM-emitted updates into the current spec.

    For scalar fields, an update overwrites the current value.
    For list fields (features, integrations, notes), the update
    is APPENDED — the LLM emits "things I learned this turn" and
    we don't want to lose previously-noted features just because
    Claude only mentioned a new one.
    """
    base_dict = current.model_dump() if current else PlatformSpec().model_dump()

    list_fields = {"features", "integrations", "notes"}

    for key, value in (updates or {}).items():
        if key not in PlatformSpec.model_fields:
            # Unknown key — Claude invented a slot, ignore.
            continue
        if value is None:
            # Explicit null = leave current value alone.
            continue
        if key in list_fields and isinstance(value, list):
            existing = list(base_dict.get(key) or [])
            for item in value:
                if isinstance(item, str) and item.strip() and item not in existing:
                    existing.append(item.strip())
            base_dict[key] = existing
        else:
            base_dict[key] = value

    # Construct via model_validate so Literal[...] types reject
    # invalid values (e.g., language="erlang" — not in our enum).
    try:
        return PlatformSpec.model_validate(base_dict)
    except Exception as exc:
        logger.warning("Spec merge failed validation, keeping previous: %s", exc)
        return current or PlatformSpec()


# ── orchestrator ───────────────────────────────────────────────────


async def run_chat_turn(input: ChatTurnInput) -> ChatTurnOutput:
    """One round-trip: user message in, assistant message + updated
    spec + ranked template suggestions out."""
    system = _build_system_prompt(input.current_spec)

    raw = await _call_claude(system, input.history, input.user_message)

    try:
        parsed = _extract_json(raw)
        assistant_message = parsed.get("assistant_message") or ""
        updates = parsed.get("spec_updates") or {}
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse Claude response as JSON: %s", exc)
        # Degraded: surface the raw text as the assistant message,
        # don't update the spec.
        assistant_message = (
            raw if raw.strip()
            else "I had trouble understanding — could you rephrase what you want to build?"
        )
        updates = {}

    new_spec = _merge_spec(input.current_spec, updates)
    suggestions = rank_for_spec(new_spec)

    return ChatTurnOutput(
        assistant_message=assistant_message,
        spec=new_spec,
        template_suggestions=suggestions,
        next_question=None,
    )
