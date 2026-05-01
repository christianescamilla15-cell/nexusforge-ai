"""Pydantic models for the Platform Synthesizer.

The Platform Synthesizer takes a conversational description of a
desired application (language, features, integrations, auth model)
and produces a fully-runnable project on disk. The shape lives
here; the chat extractor, template registry, and synthesizer all
import from this module.

Design: each user-facing field is OPTIONAL until the user lands
on it. The chat extractor fills slots gradually as the user
describes more about what they want. A template's `required_slots`
list says which fields must be non-None before it can be built.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── core spec ────────────────────────────────────────────────────────


class PlatformSpec(BaseModel):
    """The user's accumulated description of their desired project.

    Filled in slot-by-slot as the conversation progresses. Each
    chat turn re-emits the latest extracted version; the frontend
    diffs to show the user "I noticed you want X" prompts.
    """

    project_name: Optional[str] = None
    description: Optional[str] = Field(
        None, description="One-sentence summary of what the user is building"
    )

    # Stack
    language: Optional[Literal["python", "typescript", "javascript", "go", "rust"]] = None
    backend_framework: Optional[str] = None  # e.g. "fastapi", "express", "django", "gin"
    frontend_framework: Optional[Literal["react", "vue", "next", "svelte", "none"]] = None
    database: Optional[Literal["postgres", "mysql", "sqlite", "mongo", "none"]] = None

    # Capabilities (free-form list of feature strings the user mentioned)
    features: list[str] = Field(default_factory=list)

    # Auth model
    auth: Optional[Literal["none", "jwt", "google_oauth", "supabase", "auth0"]] = None

    # External integrations the user explicitly named (slack, stripe, openai, etc.)
    integrations: list[str] = Field(default_factory=list)

    # Free-form notes the chat extractor wasn't sure where to put.
    notes: list[str] = Field(default_factory=list)


# ── templates ────────────────────────────────────────────────────────


class TemplateSummary(BaseModel):
    """Lightweight info shown in the suggestion panel."""

    template_id: str
    name: str
    short_description: str
    stack: list[str]
    best_for: list[str] = Field(
        default_factory=list,
        description="Use-cases this template fits (matched against spec to score)",
    )


class TemplateMatch(BaseModel):
    """A template ranked against the current spec.

    `score` is in [0,1]. Frontend sorts suggestions by score
    descending and highlights the top one.
    """

    template: TemplateSummary
    score: float
    matched_signals: list[str] = Field(
        default_factory=list,
        description="Why this template scored where it did — debuggable",
    )


# ── chat ────────────────────────────────────────────────────────────


class ChatTurnInput(BaseModel):
    """Body of POST /api/platform-synth/chat."""

    user_message: str
    history: list[dict] = Field(
        default_factory=list,
        description="Previous turns: [{'role':'user'|'assistant','content':str}, ...]",
    )
    current_spec: Optional[PlatformSpec] = None


class ChatTurnOutput(BaseModel):
    """Response shape — the frontend reads `assistant_message` for
    the chat bubble, `spec` to update the right panel, and
    `template_suggestions` to update the template carousel."""

    assistant_message: str
    spec: PlatformSpec
    template_suggestions: list[TemplateMatch]
    next_question: Optional[str] = Field(
        None,
        description="If the assistant has a focused next question, it's also surfaced here for accessibility",
    )


# ── synthesizer ─────────────────────────────────────────────────────


class BuildRequest(BaseModel):
    """POST /api/platform-synth/build — finalize and generate.

    `target_dir` is a server-side path where the project will be
    written. The route validates it falls under a configured root
    (so users can't path-traverse).
    """

    template_id: str
    spec: PlatformSpec
    target_dir: str


class BuildResult(BaseModel):
    """What the build endpoint returns."""

    project_path: str
    files_written: int
    template_id: str
    status: Literal["complete", "partial", "failed"]
    next_steps: list[str] = Field(
        default_factory=list,
        description="Human-readable instructions to run the project (e.g., 'cd <path>', 'pip install -r ...')",
    )
    warnings: list[str] = Field(default_factory=list)
