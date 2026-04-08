"""Pydantic models for the meta-orchestration layer."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class PipelinePhase(str, Enum):
    """Phases of the multi-LLM pipeline, each mapped to a model."""
    THINK = "think"         # gemma4:27b or gemma3:4b — reasoning
    BUILD = "build"         # qwen2.5-coder:7b — structured output
    DOCUMENT = "document"   # llama3.1:8b — narrative text
    VERIFY = "verify"       # deepseek-r1:8b — critical review
    PREDICT = "predict"     # gemma3:4b — fast analysis


# Model assignment per phase
PHASE_MODEL_MAP = {
    PipelinePhase.THINK: "gemma3:4b",       # Use 27b when available
    PipelinePhase.BUILD: "qwen2.5-coder:7b",
    PipelinePhase.DOCUMENT: "llama3.1:8b",
    PipelinePhase.VERIFY: "deepseek-r1:8b",
    PipelinePhase.PREDICT: "gemma3:4b",
}

# Phases that support native thinking mode
THINKING_PHASES = {PipelinePhase.THINK, PipelinePhase.VERIFY}


class PhaseResult(BaseModel):
    """Result from a single pipeline phase."""
    phase: PipelinePhase
    model: str
    output: str
    thinking: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    duration_sec: float = 0.0
    cost_usd: float = 0.0


class PipelineResult(BaseModel):
    """Aggregated result from a multi-phase pipeline run."""
    phases: list[PhaseResult] = []
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_sec: float = 0.0
    final_output: str = ""

    def add_phase(self, result: PhaseResult):
        self.phases.append(result)
        self.total_tokens += result.tokens_input + result.tokens_output
        self.total_cost_usd += result.cost_usd
        self.total_duration_sec += result.duration_sec
        self.final_output = result.output


class BacklogItem(BaseModel):
    """A predicted feature, bugfix, or improvement."""
    title: str
    description: str
    category: str = "feature"  # feature, bugfix, refactor, performance, security
    priority: str = "medium"   # critical, high, medium, low
    estimated_effort: str = "" # small, medium, large
    rationale: str = ""
    affected_files: list[str] = []
    suggested_agents: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArchitectureDecision(BaseModel):
    """A structured architecture reasoning output."""
    summary: str
    thinking_trace: str = ""
    trade_offs: list[dict[str, str]] = []  # [{pro: "", con: ""}]
    affected_files: list[str] = []
    dependencies: list[str] = []
    risk_assessment: str = ""
    recommendation: str = ""


class KiroSpec(BaseModel):
    """A complete Kiro-compatible spec (3 files)."""
    feature_name: str
    slug: str = ""
    requirements_md: str = ""
    design_md: str = ""
    tasks_md: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        if not self.slug:
            self.slug = self.feature_name.lower().replace(" ", "-").replace("_", "-")[:50]


class EndpointSuggestion(BaseModel):
    """A suggested API endpoint based on codebase analysis."""
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str
    request_schema: str = ""
    response_schema: str = ""
    agent_dependencies: list[str] = []
    generated_code: str = ""
    confidence: float = 0.0


class DAGOptimization(BaseModel):
    """Optimized DAG execution plan."""
    original_groups: list[list[str]] = []
    optimized_groups: list[list[str]] = []
    models_to_prewarm: list[str] = []
    estimated_cost_usd: float = 0.0
    estimated_duration_sec: float = 0.0
    risk_per_step: dict[str, float] = {}  # step_name -> failure probability
    changes_made: list[str] = []  # human-readable list of optimizations


class MetaPipelineRequest(BaseModel):
    """Request to run a multi-phase pipeline."""
    prompt: str
    phases: list[PipelinePhase] = [PipelinePhase.THINK, PipelinePhase.BUILD]
    context: dict[str, Any] = {}
    max_tokens_per_phase: int = 2048


class FeaturePredictionRequest(BaseModel):
    """Request to predict next features/fixes."""
    git_log_lines: int = 20
    include_error_analysis: bool = True
    max_items: int = 5


class SpecGenerationRequest(BaseModel):
    """Request to auto-generate a Kiro spec."""
    feature_description: str
    spec_type: str = "feature"  # feature, bugfix, refactor, migration
    include_verification: bool = True
