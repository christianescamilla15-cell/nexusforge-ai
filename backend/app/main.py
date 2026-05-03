import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.client import get_db_pool, get_redis, close_connections
from app.db.mongo_client import close_mongo
from app.routes import workflows, executions, agents, documents, health, swarms, plugins, memory, auth, metrics, workflow_runs
from app.routes.enterprise_ops import router as enterprise_ops_router
from app.routes.document_intelligence import router as doc_intel_router
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
from app.routes.portfolio_copilot import router as portfolio_copilot_router
from app.routes.orchestrator import router as orchestrator_router
from app.routes.evaluation import router as evaluation_router
from app.routes.executions_db import router as executions_db_router
from app.routes.meta import router as meta_router
from app.routes.platform_synth import router as platform_synth_router
from app.observability.tracing import get_tracer

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # A-03 (2026-04-25) + H-2 Phase 1 (2026-04-27): emit fingerprints
    # of EACH derived secret at boot. Operators diff across deploys
    # to verify which secrets rotated. No secret is logged in clear
    # — only its sha256[:16] digest. Per-secret view shows whether
    # the deploy is using dedicated env vars or the legacy
    # JWT_SECRET-derived fallback.
    try:
        from app.auth.secrets import boot_fingerprints
        _fps = boot_fingerprints()
        for _name, _fp in _fps.items():
            print(f"secret fingerprint {_name}: {_fp}")
            logger.info("secret fingerprint %s: %s", _name, _fp)
    except Exception:
        # Don't block startup on a failing fingerprint computation.
        pass

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

    # Diagnostics: log SDK versions so we know which Anthropic features are reachable.
    # anthropic>=0.40 is needed for client.beta.messages.create (Context Editing, Memory Tool).
    try:
        import anthropic as _anthropic_pkg
        _anthropic_version = getattr(_anthropic_pkg, "__version__", "unknown")
        print(f"anthropic SDK version: {_anthropic_version}")
        logger.info("anthropic SDK version: %s", _anthropic_version)
    except Exception as e:
        print(f"Warning: anthropic SDK not importable: {e}")
    try:
        from app.meta.agent_sdk_bridge import _SDK_VERSION as _agent_sdk_version, _SDK_AVAILABLE
        if _SDK_AVAILABLE:
            print(f"claude-agent-sdk version: {_agent_sdk_version}")
            logger.info("claude-agent-sdk version: %s", _agent_sdk_version)
        else:
            print("claude-agent-sdk: not installed (Agent SDK bridge disabled)")
    except Exception as e:
        print(f"Warning: claude-agent-sdk diagnostics failed: {e}")

    # Start automation scheduler
    try:
        from app.routes.automations import start_scheduler
        start_scheduler()
        print("Automation scheduler started")
    except Exception as e:
        print(f"Warning: Scheduler not started: {e}")

    # Start zombie cleanup (every 5 minutes)
    import asyncio
    from app.utils.cleanup import mark_stale_runs_as_zombies

    async def _zombie_cleanup_loop():
        while True:
            await asyncio.sleep(300)  # 5 minutes
            try:
                await mark_stale_runs_as_zombies()
            except Exception as exc:
                logger.debug("Zombie cleanup skipped: %s", exc)
    _zombie_task = asyncio.create_task(_zombie_cleanup_loop())
    print("Zombie cleanup task started (every 5 min)")

    yield
    _zombie_task.cancel()
    # Shutdown
    try:
        await close_connections()
        await close_mongo()
    except Exception:
        pass

# ── Sentry Error Tracking ───────────────────────────────────────────────────
import os as _main_os  # noqa: E402 — needed at module load for SENTRY_DSN check
_sentry_dsn = _main_os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=_main_os.environ.get("NEXUSFORGE_ENV", "development"),
            release=f"nexusforge@2.0",
            integrations=[FastApiIntegration(), AsyncioIntegration()],
        )
        print("Sentry error tracking initialized")
    except ImportError:
        print("Warning: sentry-sdk not installed — error tracking disabled")
    except Exception as e:
        print(f"Warning: Sentry init failed: {e}")

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Enterprise AI Agent Orchestration + Automated Code Remediation Platform",
    lifespan=lifespan,
    redirect_slashes=True,
    # Interactive docs are exposed only in debug/dev mode. In production
    # (DEBUG=false) /docs, /redoc and /openapi.json return 404 so the full
    # API surface is not browsable by anonymous visitors.
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)


# ── Global exception handlers (Tier 2 of 2026-05-02 triangulation) ──
# FastAPI's default 422 leaks the full Pydantic field path tree, which
# in this codebase often mirrors DB column names. Default 500 leaks the
# traceback when uncaught exceptions reach the handler. Both surfaces
# are valuable for attackers mapping the schema. We replace them with
# a sanitized response that includes the X-Request-ID so legitimate
# debugging via server logs still works, while denying the public any
# internal structure.
import uuid as _uuid
from fastapi import Request as _Request
from fastapi.exceptions import RequestValidationError as _RequestValidationError
from fastapi.responses import JSONResponse as _JSONResponse


def _request_id_for(request: _Request) -> str:
    """Reuse the SecurityHeadersMiddleware request id so log + response match."""
    return request.headers.get("X-Request-ID") or str(_uuid.uuid4())[:8]


@app.exception_handler(_RequestValidationError)
async def _validation_exception_handler(request: _Request, exc: _RequestValidationError):
    rid = _request_id_for(request)
    # Full validation detail goes to server logs only.
    logger.warning(
        "validation error rid=%s path=%s errors=%s",
        rid, request.url.path, exc.errors(),
    )
    if settings.debug:
        # In dev keep the rich body so contract-drift smoke tests still
        # see the missing-field detail (e.g. 2026-05-02 harness work).
        return _JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "request_id": rid},
        )
    return _JSONResponse(
        status_code=422,
        content={"detail": "Invalid request payload", "request_id": rid},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: _Request, exc: Exception):
    rid = _request_id_for(request)
    # exception() emits stack trace to logs; client sees nothing internal.
    logger.exception("unhandled exception rid=%s path=%s", rid, request.url.path)
    return _JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": rid},
    )

# Request ID middleware — adds X-Request-ID header for debugging
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(_uuid.uuid4())[:8])
        response = await call_next(request)
        # Request tracing
        response.headers["X-Request-ID"] = request_id
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Cache: API responses should not be cached by default
        if "/api/" in str(request.url):
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        # Version
        response.headers["X-Powered-By"] = "NexusForge AI v2.5"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# GZip compression — reduces response size for large JSON payloads
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)

# Auth middleware — injects user into request.state
# Must be added BEFORE CORS so CORS wraps it (outermost = last added)
from app.auth.middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# CORS — outermost middleware so ALL responses (including 401s) get CORS headers
# Must be added LAST so it wraps everything, including AuthMiddleware 401 responses
#
# H-5 (2026-04-25): explicit method + header allowlist. Prior config
# used `allow_methods=["*"]` and `allow_headers=["*"]`, which combined
# with a stale Vercel preview alias in `ALLOWED_ORIGINS` made
# preview-hijack class attacks (where a redeployed preview suddenly
# satisfies CORS) more impactful. With `allow_credentials=False` the
# wildcard origin remains acceptable as a fallback (browsers don't
# auto-send credentials), but methods and headers are now bounded.
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()] if settings.allowed_origins else ["*"]
import os as _main_os
if _origins == ["*"] and _main_os.environ.get("NEXUSFORGE_ENV") == "production":
    logging.getLogger("nexusforge.cors").warning("CORS: wildcard origins in production — set ALLOWED_ORIGINS env var")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Mythos-Key",
        "X-NexusForge-Signature",
        "X-Request-ID",
        "Accept",
        "Accept-Language",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

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
app.include_router(enterprise_ops_router, prefix="/api")
app.include_router(doc_intel_router, prefix="/api")
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

from app.routes.sdk import router as sdk_router
app.include_router(sdk_router, prefix="/api", tags=["agent-sdk"])

from app.routes.refactor import router as refactor_router
app.include_router(refactor_router, prefix="/api", tags=["refactor-engine"])

from app.routes.organizations import router as org_router
app.include_router(org_router, prefix="/api", tags=["organizations"])

from app.routes.admin import router as admin_router
app.include_router(admin_router, prefix="/api", tags=["admin"])

# 2026-04-30: previously-unregistered route modules. Each was implemented
# but never wired into the FastAPI app, so the documented endpoints 404'd.
# `meta_router` already declares `prefix="/api/meta"` internally — register
# WITHOUT an extra `/api` prefix or it becomes `/api/api/meta/*`.
app.include_router(portfolio_copilot_router, prefix="/api", tags=["portfolio-copilot"])
app.include_router(orchestrator_router, prefix="/api", tags=["orchestrator"])
app.include_router(evaluation_router, prefix="/api", tags=["evaluation"])
app.include_router(executions_db_router, prefix="/api", tags=["executions-db"])
app.include_router(meta_router, tags=["meta-orchestration"])

# 2026-05-01: Platform Synthesizer — chat-driven project generator.
# User describes desired stack/features in natural language; module
# extracts a structured PlatformSpec, ranks matching templates, and
# (on build) writes a runnable project tree under PLATFORM_SYNTH_ROOT.
app.include_router(platform_synth_router, prefix="/api", tags=["platform-synth"])

# Mythos — OWNER-ONLY security auditor (returns 404 without valid key)
from app.security.routes import router as mythos_router
app.include_router(mythos_router, prefix="/api", tags=["mythos"])


# ── API Versioning ──────────────────────────────────────────────────────────
# T2.1 (2026-04-30 triangulation): the original comment claimed that
# /api/v1/* was a full mirror of /api/* and that clients should migrate.
# In reality, only a CURATED PUBLIC-API SUBSET is mirrored — the
# routers below — and that set is intentional, not exhaustive.
# Internal/dev tooling (workflows, executions, agents, swarms, memory,
# metrics, refactor-engine internals, connectors, templates, rules,
# variables, audit, demo, mythos, meta, orchestrator, evaluation,
# executions-db, portfolio-copilot, document-intelligence,
# enterprise-ops, integrations, feedback, drive-pipeline,
# workflow_runs) stays unversioned at /api/* and may break across
# releases.
#
# If a router is added to the mirror below, it joins the v1 stability
# contract: backwards-compatible shape changes only, deprecation
# windows for breaking changes. Add to the list deliberately.
from fastapi import APIRouter as _APIRouter

_v1 = _APIRouter(prefix="/api/v1", tags=["v1"])

@_v1.get("/version")
async def api_version():
    return {"version": "v1", "latest": "v1", "deprecated": []}

app.include_router(_v1)

# Curated v1 public surface. Each router here is a stability contract.
_V1_PUBLIC_ROUTERS = [
    auth_routes, billing_routes, api_keys_routes, wizard_routes,
    results_router, analyze_router, automations_router, sdk_router,
    refactor_router, org_router, admin_router,
]
for _r in _V1_PUBLIC_ROUTERS:
    app.include_router(_r, prefix="/api/v1")

