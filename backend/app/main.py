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
from app.observability.tracing import get_tracer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — graceful: don't crash if DB/Redis unavailable
    try:
        get_tracer()
    except Exception:
        print("Warning: OpenTelemetry tracing not available")
    try:
        await get_db_pool()
        print("PostgreSQL connected")
    except Exception as e:
        print(f"Warning: PostgreSQL not available: {e}")
    try:
        await get_redis()
        print("Redis connected")
    except Exception as e:
        print(f"Warning: Redis not available: {e}")
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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(executions.router, prefix="/api/executions", tags=["executions"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(swarms.router, prefix="/api/swarms", tags=["swarms"])
app.include_router(plugins.router, prefix="/api/plugins", tags=["plugins"])
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
