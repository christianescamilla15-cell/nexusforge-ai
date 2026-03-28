from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.client import get_db_pool, get_redis, close_connections
from app.db.mongo_client import close_mongo
from app.routes import workflows, executions, agents, documents, health, swarms, plugins, memory, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_db_pool()
    await get_redis()
    yield
    # Shutdown
    await close_connections()
    await close_mongo()

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
