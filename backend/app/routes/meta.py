"""Meta-orchestration API routes.

Exposes the multi-LLM pipeline, feature prediction, architecture reasoning,
spec generation, and flow optimization via REST endpoints.
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/api/meta", tags=["meta-orchestration"])
logger = logging.getLogger(__name__)


# ── Request/Response models ──────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    prompt: str
    phases: list[str] = ["think", "build"]
    context: dict[str, Any] = {}
    max_tokens: int = 2048


class ReasonRequest(BaseModel):
    feature_description: str
    codebase_context: str = ""


class SpecRequest(BaseModel):
    feature_description: str
    spec_type: str = "feature"
    verify: bool = True
    write_to_disk: bool = False


class PredictRequest(BaseModel):
    git_log_lines: int = 20
    include_errors: bool = True
    max_items: int = 5


class OptimizeRequest(BaseModel):
    step_names: list[str]
    parallel_groups: list[list[str]]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/pipeline")
async def run_pipeline(body: PipelineRequest):
    """Run a multi-phase LLM pipeline (THINK → BUILD → VERIFY → DOCUMENT)."""
    from app.meta.pipeline import get_pipeline
    from app.meta.schemas import PipelinePhase

    phase_map = {p.value: p for p in PipelinePhase}
    phases = [phase_map[p] for p in body.phases if p in phase_map]

    if not phases:
        return {"error": "No valid phases specified"}

    pipeline = get_pipeline()
    result = await pipeline.run(
        prompt=body.prompt,
        phases=phases,
        context=body.context,
        max_tokens=body.max_tokens,
    )

    return {
        "phases": [
            {
                "phase": pr.phase.value,
                "model": pr.model,
                "output": pr.output,
                "thinking": pr.thinking,
                "tokens": pr.tokens_input + pr.tokens_output,
                "duration_sec": pr.duration_sec,
                "cost_usd": pr.cost_usd,
            }
            for pr in result.phases
        ],
        "final_output": result.final_output,
        "total_tokens": result.total_tokens,
        "total_cost_usd": result.total_cost_usd,
        "total_duration_sec": result.total_duration_sec,
    }


@router.post("/reason")
async def reason_architecture(body: ReasonRequest):
    """Reason about an architecture decision using thinking mode."""
    from app.meta.architecture_reasoner import ArchitectureReasoner

    reasoner = ArchitectureReasoner()
    decision = await reasoner.reason(
        feature_description=body.feature_description,
        codebase_context=body.codebase_context,
    )

    return {
        "summary": decision.summary,
        "thinking_trace": decision.thinking_trace[:2000] if decision.thinking_trace else "",
        "trade_offs": decision.trade_offs,
        "affected_files": decision.affected_files,
        "dependencies": decision.dependencies,
        "risk_assessment": decision.risk_assessment,
        "recommendation": decision.recommendation,
    }


@router.post("/generate-spec")
async def generate_spec(body: SpecRequest):
    """Auto-generate a Kiro-compatible spec from a feature description."""
    from app.meta.spec_generator import SpecGenerator

    generator = SpecGenerator()
    spec = await generator.generate(
        feature_description=body.feature_description,
        spec_type=body.spec_type,
        verify=body.verify,
    )

    result = {
        "feature_name": spec.feature_name,
        "slug": spec.slug,
        "requirements_md": spec.requirements_md,
        "design_md": spec.design_md,
        "tasks_md": spec.tasks_md,
        "generated_at": spec.generated_at.isoformat(),
    }

    if body.write_to_disk:
        try:
            path = generator.write_to_disk(spec, ".")
            result["written_to"] = path
        except Exception as e:
            result["write_error"] = str(e)

    return result


@router.post("/predict-features")
async def predict_features(body: PredictRequest):
    """Predict next features, fixes, or improvements needed."""
    from app.meta.feature_predictor import FeaturePredictor

    predictor = FeaturePredictor(".")
    items = await predictor.predict(
        git_log_lines=body.git_log_lines,
        include_errors=body.include_errors,
        max_items=body.max_items,
    )

    return {
        "predictions": [item.model_dump() for item in items],
        "count": len(items),
    }


@router.post("/optimize-flow")
async def optimize_flow(body: OptimizeRequest):
    """Optimize a workflow DAG using predictive memory."""
    from app.meta.flow_optimizer import FlowOptimizer

    optimizer = FlowOptimizer()
    result = await optimizer.optimize(body.step_names, body.parallel_groups)

    return result.model_dump()


class SDKRequest(BaseModel):
    prompt: str
    tools: list[str] = ["Read", "Glob", "Grep"]
    resume_session: bool = False


@router.post("/sdk/run")
async def run_sdk(body: SDKRequest):
    """Run a task through the Claude Agent SDK (requires ANTHROPIC_API_KEY)."""
    from app.meta.agent_sdk_bridge import get_sdk_bridge

    bridge = get_sdk_bridge()
    if not bridge.available:
        return {"error": "Agent SDK not available. Install claude-agent-sdk and set ANTHROPIC_API_KEY."}

    result = await bridge.run(
        prompt=body.prompt,
        tools=body.tools,
        resume_session=body.resume_session,
    )
    return result


@router.post("/sdk/review")
async def sdk_code_review(body: dict):
    """Use Agent SDK to review a file."""
    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    return await bridge.code_review(body.get("file_path", ""))


@router.post("/sdk/research")
async def sdk_research(body: dict):
    """Use Agent SDK to research a topic."""
    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    return await bridge.research(body.get("topic", ""))


@router.get("/health")
async def meta_health():
    """Check meta-orchestration subsystem health."""
    from app.meta.pipeline import get_pipeline
    from app.meta.agent_sdk_bridge import get_sdk_bridge

    pipeline = get_pipeline()
    bridge = get_sdk_bridge()
    router_ok = pipeline._get_router() is not None

    return {
        "status": "ok" if router_ok else "degraded",
        "pipeline": "ready" if router_ok else "no router",
        "agent_sdk": "available" if bridge.available else "not configured",
        "agents": [
            "ArchitectureReasoner",
            "SpecGenerator",
            "FeaturePredictor",
            "FlowOptimizer",
            "MetaPipeline",
            "AgentSDKBridge",
        ],
        "phases": ["think", "build", "document", "verify", "predict"],
        "endpoints": [
            "/api/meta/pipeline",
            "/api/meta/reason",
            "/api/meta/generate-spec",
            "/api/meta/predict-features",
            "/api/meta/optimize-flow",
            "/api/meta/sdk/run",
            "/api/meta/sdk/review",
            "/api/meta/sdk/research",
        ],
    }
