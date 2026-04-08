"""Tests for the meta-orchestration layer."""

import pytest
from app.meta.schemas import (
    PipelinePhase, PhaseResult, PipelineResult, BacklogItem,
    ArchitectureDecision, KiroSpec, EndpointSuggestion, DAGOptimization,
    PHASE_MODEL_MAP, THINKING_PHASES, MetaPipelineRequest,
)


class TestSchemas:
    def test_pipeline_phases(self):
        assert PipelinePhase.THINK.value == "think"
        assert PipelinePhase.BUILD.value == "build"
        assert PipelinePhase.DOCUMENT.value == "document"
        assert PipelinePhase.VERIFY.value == "verify"
        assert PipelinePhase.PREDICT.value == "predict"

    def test_phase_model_map(self):
        assert "gemma" in PHASE_MODEL_MAP[PipelinePhase.THINK]
        assert "qwen" in PHASE_MODEL_MAP[PipelinePhase.BUILD]
        assert "llama" in PHASE_MODEL_MAP[PipelinePhase.DOCUMENT]
        assert "deepseek" in PHASE_MODEL_MAP[PipelinePhase.VERIFY]

    def test_thinking_phases(self):
        assert PipelinePhase.THINK in THINKING_PHASES
        assert PipelinePhase.VERIFY in THINKING_PHASES
        assert PipelinePhase.BUILD not in THINKING_PHASES

    def test_pipeline_result_accumulation(self):
        result = PipelineResult()
        result.add_phase(PhaseResult(
            phase=PipelinePhase.THINK, model="gemma3:4b",
            output="analysis here", tokens_input=100, tokens_output=200,
            duration_sec=1.5, cost_usd=0.0,
        ))
        result.add_phase(PhaseResult(
            phase=PipelinePhase.BUILD, model="qwen2.5-coder:7b",
            output="code here", tokens_input=150, tokens_output=300,
            duration_sec=2.0, cost_usd=0.0,
        ))
        assert result.total_tokens == 750
        assert result.total_duration_sec == 3.5
        assert result.final_output == "code here"
        assert len(result.phases) == 2

    def test_backlog_item(self):
        item = BacklogItem(
            title="Add caching",
            description="API responses are slow",
            category="performance",
            priority="high",
        )
        assert item.category == "performance"
        assert item.priority == "high"

    def test_kiro_spec_slug(self):
        spec = KiroSpec(feature_name="Fix Auth Token Refresh")
        assert spec.slug == "fix-auth-token-refresh"

    def test_kiro_spec_custom_slug(self):
        spec = KiroSpec(feature_name="test", slug="custom-slug")
        assert spec.slug == "custom-slug"

    def test_architecture_decision(self):
        d = ArchitectureDecision(
            summary="Use Redis for caching",
            trade_offs=[{"pro": "Fast reads", "con": "Extra infra"}],
            recommendation="Implement with TTL-based eviction",
        )
        assert len(d.trade_offs) == 1
        assert d.thinking_trace == ""

    def test_dag_optimization(self):
        opt = DAGOptimization(
            original_groups=[["a", "b"], ["c"]],
            optimized_groups=[["b", "a"], ["c"]],
            changes_made=["Reordered group 0 for fail-fast"],
        )
        assert opt.original_groups != opt.optimized_groups
        assert len(opt.changes_made) == 1

    def test_meta_pipeline_request(self):
        req = MetaPipelineRequest(prompt="Design a caching layer")
        assert req.phases == [PipelinePhase.THINK, PipelinePhase.BUILD]
        assert req.max_tokens_per_phase == 2048


class TestPipeline:
    def test_import(self):
        from app.meta.pipeline import MetaPipeline, get_pipeline
        p = get_pipeline()
        assert p is not None

    def test_phase_system_prompts(self):
        from app.meta.pipeline import PHASE_SYSTEM_PROMPTS
        for phase in PipelinePhase:
            assert phase in PHASE_SYSTEM_PROMPTS
            assert len(PHASE_SYSTEM_PROMPTS[phase]) > 20

    def test_singleton(self):
        from app.meta.pipeline import get_pipeline
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2


class TestArchitectureReasoner:
    def test_import(self):
        from app.meta.architecture_reasoner import ArchitectureReasoner
        r = ArchitectureReasoner()
        assert r is not None

    def test_split_sections(self):
        from app.meta.architecture_reasoner import _split_sections
        text = "### Summary\nThis is a summary\n### Risk Assessment\nHigh risk"
        sections = _split_sections(text)
        assert "summary" in sections
        assert "risk assessment" in sections
        assert "This is a summary" in sections["summary"]

    def test_extract_file_list(self):
        from app.meta.architecture_reasoner import _extract_file_list
        text = "- `app/routes/auth.py`\n- `app/models/user.py`\n- some/path.js"
        files = _extract_file_list(text)
        assert "app/routes/auth.py" in files
        assert "app/models/user.py" in files


class TestSpecGenerator:
    def test_import(self):
        from app.meta.spec_generator import SpecGenerator
        g = SpecGenerator()
        assert g is not None

    def test_parse_spec(self):
        from app.meta.spec_generator import SpecGenerator
        g = SpecGenerator()
        output = "# Requirements\nReq 1\n---SPLIT---\n# Design\nDesign 1\n---SPLIT---\n# Tasks\n- [ ] Task 1"
        spec = g._parse_spec("Test Feature", output)
        assert "Requirements" in spec.requirements_md
        assert "Design" in spec.design_md
        assert "Task 1" in spec.tasks_md
        assert spec.slug == "test-feature"

    def test_parse_spec_partial(self):
        from app.meta.spec_generator import SpecGenerator
        g = SpecGenerator()
        spec = g._parse_spec("Test", "Only requirements here")
        assert "Only requirements here" in spec.requirements_md
        assert "Generation failed" in spec.design_md


class TestFeaturePredictor:
    def test_import(self):
        from app.meta.feature_predictor import FeaturePredictor
        fp = FeaturePredictor(".")
        assert fp.project_dir == "."

    def test_parse_backlog(self):
        from app.meta.feature_predictor import FeaturePredictor
        fp = FeaturePredictor()
        output = (
            "ITEM: Add API rate limiting\n"
            "CATEGORY: security\n"
            "PRIORITY: high\n"
            "EFFORT: medium\n"
            "RATIONALE: Prevent abuse\n"
            "FILES: app/routes/auth.py, app/middleware.py\n"
            "AGENTS: ValidatorAgent, ComplianceAgent\n"
            "---\n"
            "ITEM: Fix slow queries\n"
            "CATEGORY: performance\n"
            "PRIORITY: medium\n"
            "EFFORT: small\n"
            "RATIONALE: Dashboard loads slowly\n"
            "FILES: app/routes/workflow_runs.py\n"
            "AGENTS: AnalyzerAgent\n"
        )
        items = fp._parse_backlog(output, 5)
        assert len(items) == 2
        assert items[0].title == "Add API rate limiting"
        assert items[0].category == "security"
        assert items[0].priority == "high"
        assert "app/routes/auth.py" in items[0].affected_files
        assert "ValidatorAgent" in items[0].suggested_agents


class TestFlowOptimizer:
    def test_import(self):
        from app.meta.flow_optimizer import FlowOptimizer
        fo = FlowOptimizer()
        assert fo is not None


class TestMetaRoutes:
    def test_import(self):
        from app.routes.meta import router
        assert router is not None
        routes = [r.path for r in router.routes]
        assert "/api/meta/pipeline" in routes
        assert "/api/meta/reason" in routes
        assert "/api/meta/generate-spec" in routes
        assert "/api/meta/predict-features" in routes
        assert "/api/meta/optimize-flow" in routes
        assert "/api/meta/health" in routes


class TestRouterMetaAgents:
    def test_meta_agents_in_model_map(self):
        from app.llm.router import _AGENT_MODEL_MAP
        meta_agents = [
            "MetaThinkAgent", "MetaBuildAgent", "MetaDocumentAgent",
            "MetaVerifyAgent", "MetaPredictAgent",
            "FeaturePredictorAgent", "ArchitectureReasonerAgent",
            "SpecGeneratorAgent", "FlowOptimizerAgent",
        ]
        for agent in meta_agents:
            assert agent in _AGENT_MODEL_MAP, f"{agent} missing from model map"
