import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.client import get_db_pool, get_redis, close_connections
from app.db.mongo_client import close_mongo
from app.routes import workflows, executions, agents, documents, health, swarms, plugins, memory, auth, metrics, workflow_runs, executions_db, evaluation
from app.routes.enterprise_ops import router as enterprise_ops_router
from app.routes.document_intelligence import router as doc_intel_router
from app.routes.portfolio_copilot import router as portfolio_copilot_router
from app.routes.integrations import router as integrations_router
from app.routes.feedback import router as feedback_router
from app.routes.drive_pipeline import router as drive_pipeline_router
from app.routes.analyze import router as analyze_router
from app.routes.automations import router as automations_router
from app.routes.connectors import router as connectors_router
from app.routes.templates import router as templates_router
from app.routes.rules import router as rules_router
from app.routes.variables import router as variables_router
from app.routes.audit import router as audit_log_router
from app.observability.tracing import get_tracer

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — graceful: don't crash if DB/Redis unavailable
    try:
        get_tracer()
    except Exception:
        print("Warning: OpenTelemetry tracing not available")
    try:
        pool = await get_db_pool()
        from app.db.migrator import run_migrations
        summary = await run_migrations(pool)
        logger.info("DB connected, migrations: %s", summary)
        app.state.db_available = True
        print("PostgreSQL connected")
    except Exception as e:
        logger.warning("DB unavailable — running in degraded mode: %s", e)
        app.state.db_available = False
        print(f"Warning: PostgreSQL not available: {e}")
    try:
        await get_redis()
        app.state.redis_available = True
        print("Redis connected")
    except Exception as e:
        app.state.redis_available = False
        print(f"Warning: Redis not available: {e}")

    # Start automation scheduler
    try:
        from app.routes.automations import start_scheduler
        start_scheduler()
        print("Automation scheduler started")
    except Exception as e:
        print(f"Warning: Scheduler not started: {e}")

    yield
    # Shutdown
    try:
        await close_connections()
        await close_mongo()
    except Exception:
        pass

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Enterprise-grade AI Agent Orchestration Platform",
    lifespan=lifespan,
    redirect_slashes=True,
)

# CORS — use ALLOWED_ORIGINS env var; fallback to permissive for dev
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()] if settings.allowed_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware — injects user into request.state (non-blocking for now)
from app.auth.middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# Auth + Billing + API Keys + Audit + Custom Agents + Slack
from app.auth.routes import router as auth_routes
from app.auth.billing import router as billing_routes
from app.auth.api_keys import router as api_keys_routes
from app.auth.audit import router as audit_routes
from app.routes.custom_agents import router as custom_agents_routes
from app.integrations.slack.client import router as slack_routes
app.include_router(auth_routes, prefix="/api")
app.include_router(billing_routes, prefix="/api")
app.include_router(api_keys_routes, prefix="/api")
app.include_router(audit_routes, prefix="/api")
app.include_router(custom_agents_routes, prefix="/api")
app.include_router(slack_routes, prefix="/api")

from app.routes.wizard import router as wizard_routes
app.include_router(wizard_routes, prefix="/api")

from app.routes.wizard_chat import router as wizard_chat_router
app.include_router(wizard_chat_router, prefix="/api", tags=["wizard-chat"])

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(executions.router, prefix="/api/executions", tags=["executions"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(swarms.router, prefix="/api/swarms", tags=["swarms"])
app.include_router(plugins.router, prefix="/api/plugins", tags=["plugins"])

from app.routes.results import router as results_router
app.include_router(results_router, prefix="/api", tags=["results"])
app.include_router(memory.router, prefix="/api", tags=["memory"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(workflow_runs.router, prefix="/api", tags=["workflow-runs"])
app.include_router(executions_db.router, prefix="/api", tags=["executions-db"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
app.include_router(enterprise_ops_router, prefix="/api")
app.include_router(doc_intel_router, prefix="/api")
app.include_router(portfolio_copilot_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(drive_pipeline_router, prefix="/api")
app.include_router(analyze_router, prefix="/api", tags=["analyze"])
app.include_router(automations_router, prefix="/api", tags=["automations"])
app.include_router(connectors_router, prefix="/api", tags=["connectors"])
app.include_router(templates_router, prefix="/api", tags=["templates"])
app.include_router(rules_router, prefix="/api", tags=["rules"])
app.include_router(variables_router, prefix="/api", tags=["variables"])
app.include_router(audit_log_router, prefix="/api", tags=["audit-log"])

from app.routes.demo import router as demo_router
app.include_router(demo_router, prefix="/api", tags=["demo"])
