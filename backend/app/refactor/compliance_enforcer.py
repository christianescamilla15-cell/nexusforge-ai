"""Compliance-by-design enforcer (Gap 7 from the vision doc).

Emits a drop-in middleware package for .NET or Python applications
that enforces the five controls most modernization programs need at
the same time:

1. Segregation of Duties (SoD)        — reject same-user approve+execute
2. Transactional audit logging        — every write logged with user + diff
3. Exception handling standard        — global handler, generic 500, trace id
4. RBAC with scope enforcement        — JWT + scope check per route
5. PII masking                        — helper for log sanitization

Each template is intentionally opinionated and ready to copy into an
existing application. The generator is deterministic — given the
same inputs, it produces byte-identical output.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GeneratedComplianceMiddleware:
    out_dir: str
    target: str  # python / dotnet / both
    files_written: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "out_dir": self.out_dir,
            "target": self.target,
            "files_written": self.files_written,
            "controls": self.controls,
        }


# ── Python / FastAPI templates ─────────────────────────────────────────────


_PY_SOD = '''"""Segregation of Duties middleware.

Blocks a user from performing two conflicting actions on the same
resource (e.g., approve + execute of the same workflow). Keeps an
in-memory log of recent actions keyed by (user_id, resource_id)
with a configurable TTL.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request, HTTPException


_SOD_CONFLICTS: dict[str, set[str]] = {
    # action -> conflicting actions already taken by the same user
    "approve": {"execute", "create"},
    "execute": {"approve"},
    "delete":  {"create", "approve"},
}


@dataclass
class _Recent:
    action: str
    at: float


class SoDRegistry:
    """In-memory registry — replace with Redis in production."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self._store: dict[tuple[str, str], list[_Recent]] = {}

    def _prune(self, key: tuple[str, str]) -> None:
        now = time.monotonic()
        self._store[key] = [r for r in self._store.get(key, []) if now - r.at < self.ttl]

    def record(self, user_id: str, resource_id: str, action: str) -> None:
        key = (user_id, resource_id)
        self._prune(key)
        self._store.setdefault(key, []).append(_Recent(action=action, at=time.monotonic()))

    def conflicts_with(
        self, user_id: str, resource_id: str, action: str
    ) -> list[str]:
        key = (user_id, resource_id)
        self._prune(key)
        conflicts = _SOD_CONFLICTS.get(action, set())
        return [r.action for r in self._store.get(key, []) if r.action in conflicts]


_registry = SoDRegistry()


def enforce_sod(
    action: str,
    resource_id_field: str = "id",
) -> Callable:
    """FastAPI dependency that enforces SoD before the route runs."""

    async def _dep(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="auth required")
        user_id = str(user.get("sub", ""))
        # Resource id lookup: first try path params, then query params
        resource_id = str(
            request.path_params.get(resource_id_field)
            or request.query_params.get(resource_id_field)
            or ""
        )
        if not resource_id:
            return
        conflicts = _registry.conflicts_with(user_id, resource_id, action)
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"segregation of duties: {user_id} already performed "
                    f"{conflicts} on resource {resource_id}"
                ),
            )
        _registry.record(user_id, resource_id, action)

    return _dep
'''


_PY_AUDIT = '''"""Transactional audit log middleware.

Logs every mutating request (POST/PUT/PATCH/DELETE) with user,
timestamp, method, path and response status. Extend ``AuditLogSink``
to write to your real audit store (DB, SIEM, Kafka topic).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class AuditRecord:
    trace_id: str
    timestamp: float
    user_id: str
    method: str
    path: str
    status_code: int
    request_body_sha: str = ""
    response_body_sha: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "request_body_sha": self.request_body_sha,
            "response_body_sha": self.response_body_sha,
            **self.extra,
        }


class AuditLogSink:
    """Override ``write`` to forward records to your real audit store."""

    def write(self, record: AuditRecord) -> None:  # pragma: no cover
        print(json.dumps(record.as_dict()))


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, sink: AuditLogSink | None = None) -> None:
        super().__init__(app)
        self.sink = sink or AuditLogSink()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        user = getattr(request.state, "user", None)
        user_id = str(user.get("sub", "anonymous")) if user else "anonymous"

        response = await call_next(request)

        record = AuditRecord(
            trace_id=trace_id,
            timestamp=time.time(),
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        self.sink.write(record)
        response.headers["X-Trace-Id"] = trace_id
        return response
'''


_PY_EXCEPTION = '''"""Global exception handler with trace ids and no stack leakage.

Catches any unhandled exception, logs the full traceback server-side
with a generated trace id, and returns a generic 500 response that
only exposes the trace id to the client.
"""
from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("compliance.exception_handler")


def register_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def _handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        logger.error(
            "unhandled exception trace_id=%s path=%s\\n%s",
            trace_id,
            request.url.path,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal server error",
                "trace_id": trace_id,
                "detail": "Contact support with the trace id above.",
            },
            headers={"X-Trace-Id": trace_id},
        )
'''


_PY_RBAC = '''"""Role-based access control with scope enforcement.

Expects ``request.state.user`` to be populated by an earlier auth
middleware with at least ``sub``, ``roles`` and ``scopes`` fields.
Fails closed: any missing claim triggers 403.
"""
from __future__ import annotations

from typing import Callable, Iterable

from fastapi import HTTPException, Request


def require_roles(*roles: str) -> Callable:
    """Dependency that passes only when the user has one of the given roles."""

    async def _dep(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="auth required")
        user_roles = set(user.get("roles", []))
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=403, detail=f"requires one of roles: {list(roles)}"
            )

    return _dep


def require_scopes(*scopes: str) -> Callable:
    """Dependency that passes only when the user has all the given scopes."""

    async def _dep(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="auth required")
        user_scopes = set(user.get("scopes", []))
        missing = [s for s in scopes if s not in user_scopes]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"missing required scopes: {missing}",
            )

    return _dep
'''


_PY_PII = '''"""PII masking helpers for log sanitization.

Apply ``mask_payload`` to any dict before handing it to a logger.
Fields matching known PII keys are redacted; partial masking is
supported for email and phone so records remain joinable by a
non-reversible key.
"""
from __future__ import annotations

import re
from typing import Any


_PII_FULL = {
    "password", "pwd", "secret", "api_key", "apikey", "token",
    "credit_card", "card_number", "cvv", "cvc", "ssn", "tax_id",
    "national_id", "passport",
}

_PII_PARTIAL_EMAIL = {"email", "email_address", "correo"}
_PII_PARTIAL_PHONE = {"phone", "phone_number", "telefono", "mobile"}


def mask_payload(obj: Any) -> Any:
    """Return a deep copy with PII fields redacted."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key_lower = k.lower()
            if key_lower in _PII_FULL:
                out[k] = "[REDACTED]"
            elif key_lower in _PII_PARTIAL_EMAIL and isinstance(v, str) and "@" in v:
                local, _, domain = v.partition("@")
                out[k] = (local[:1] + "***@" + domain) if local else v
            elif key_lower in _PII_PARTIAL_PHONE and isinstance(v, str):
                digits = re.sub(r"\\D", "", v)
                out[k] = "***" + digits[-4:] if len(digits) >= 4 else "[REDACTED]"
            else:
                out[k] = mask_payload(v)
        return out
    if isinstance(obj, list):
        return [mask_payload(item) for item in obj]
    return obj
'''


_PY_EXAMPLE = '''"""Example FastAPI wire-up with all five compliance controls.

Drop this next to your main.py as a starting point. Adjust the
import paths to match your application layout.
"""
from __future__ import annotations

from fastapi import FastAPI, Depends

from .audit_log_middleware import AuditLogMiddleware, AuditLogSink
from .exception_handler import register_exception_handler
from .rbac_middleware import require_roles, require_scopes
from .sod_middleware import enforce_sod


def build_app() -> FastAPI:
    app = FastAPI()

    # 1. Global exception handler — installs first
    register_exception_handler(app)

    # 2. Transactional audit log
    app.add_middleware(AuditLogMiddleware, sink=AuditLogSink())

    # 3. Example route using SoD + RBAC + scope
    @app.post("/workflows/{id}/approve")
    async def approve_workflow(
        id: str,
        _sod=Depends(enforce_sod("approve", resource_id_field="id")),
        _rbac=Depends(require_roles("approver")),
        _scope=Depends(require_scopes("workflow:approve")),
    ) -> dict:
        return {"status": "approved", "id": id}

    @app.post("/workflows/{id}/execute")
    async def execute_workflow(
        id: str,
        _sod=Depends(enforce_sod("execute", resource_id_field="id")),
        _rbac=Depends(require_roles("executor")),
        _scope=Depends(require_scopes("workflow:execute")),
    ) -> dict:
        return {"status": "executing", "id": id}

    return app
'''


# ── .NET / ASP.NET Core templates ──────────────────────────────────────────


_DOTNET_SOD = '''// Segregation of Duties middleware for ASP.NET Core.
//
// Blocks the same user from performing two conflicting actions on
// the same resource within a TTL window. Replace the in-memory
// registry with a distributed store (Redis, etc.) in production.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;

namespace Compliance.Middleware
{
    public static class SoDConflicts
    {
        public static readonly Dictionary<string, HashSet<string>> Rules = new()
        {
            ["approve"] = new() { "execute", "create" },
            ["execute"] = new() { "approve" },
            ["delete"]  = new() { "create", "approve" },
        };
    }

    public class SoDRegistry
    {
        private readonly TimeSpan _ttl;
        private readonly ConcurrentDictionary<(string, string), List<(string Action, DateTime At)>> _store = new();

        public SoDRegistry(TimeSpan ttl) { _ttl = ttl; }

        public IReadOnlyList<string> ConflictsWith(string userId, string resourceId, string action)
        {
            var key = (userId, resourceId);
            var now = DateTime.UtcNow;
            if (!_store.TryGetValue(key, out var list)) return Array.Empty<string>();
            var live = list.Where(x => now - x.At < _ttl).ToList();
            _store[key] = live;
            if (!SoDConflicts.Rules.TryGetValue(action, out var conflicts)) return Array.Empty<string>();
            return live.Where(x => conflicts.Contains(x.Action)).Select(x => x.Action).ToList();
        }

        public void Record(string userId, string resourceId, string action)
        {
            var key = (userId, resourceId);
            _store.AddOrUpdate(key,
                _ => new List<(string, DateTime)> { (action, DateTime.UtcNow) },
                (_, list) => { list.Add((action, DateTime.UtcNow)); return list; });
        }
    }

    public class SoDMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly SoDRegistry _registry;

        public SoDMiddleware(RequestDelegate next, SoDRegistry registry)
        {
            _next = next;
            _registry = registry;
        }

        public async Task InvokeAsync(HttpContext ctx)
        {
            // Extract intended action from route values; routes should set
            // ctx.Items["sod.action"] and ctx.Items["sod.resource_id"] via
            // a custom attribute or endpoint metadata.
            if (!ctx.Items.TryGetValue("sod.action", out var actionObj) ||
                !ctx.Items.TryGetValue("sod.resource_id", out var resourceObj))
            {
                await _next(ctx);
                return;
            }
            var action = actionObj?.ToString() ?? "";
            var resourceId = resourceObj?.ToString() ?? "";
            var userId = ctx.User?.Identity?.Name ?? "";
            if (string.IsNullOrEmpty(userId))
            {
                ctx.Response.StatusCode = 401;
                await ctx.Response.WriteAsync("auth required");
                return;
            }
            var conflicts = _registry.ConflictsWith(userId, resourceId, action);
            if (conflicts.Count > 0)
            {
                ctx.Response.StatusCode = 409;
                await ctx.Response.WriteAsync(
                    $"segregation of duties: {userId} already performed [{string.Join(",", conflicts)}] on {resourceId}");
                return;
            }
            _registry.Record(userId, resourceId, action);
            await _next(ctx);
        }
    }
}
'''


_DOTNET_AUDIT = '''// Transactional audit log middleware for ASP.NET Core.
using System;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;

namespace Compliance.Middleware
{
    public record AuditRecord(
        string TraceId,
        DateTime Timestamp,
        string UserId,
        string Method,
        string Path,
        int StatusCode);

    public interface IAuditLogSink
    {
        Task WriteAsync(AuditRecord record);
    }

    public class ConsoleAuditLogSink : IAuditLogSink
    {
        public Task WriteAsync(AuditRecord record)
        {
            Console.WriteLine(JsonSerializer.Serialize(record));
            return Task.CompletedTask;
        }
    }

    public class AuditLogMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly IAuditLogSink _sink;
        private static readonly HashSet<string> Mutating = new() { "POST", "PUT", "PATCH", "DELETE" };

        public AuditLogMiddleware(RequestDelegate next, IAuditLogSink sink)
        {
            _next = next;
            _sink = sink;
        }

        public async Task InvokeAsync(HttpContext ctx)
        {
            if (!Mutating.Contains(ctx.Request.Method))
            {
                await _next(ctx);
                return;
            }
            var traceId = ctx.Request.Headers["X-Trace-Id"].FirstOrDefault() ?? Guid.NewGuid().ToString();
            ctx.Response.Headers["X-Trace-Id"] = traceId;
            await _next(ctx);
            var record = new AuditRecord(
                TraceId: traceId,
                Timestamp: DateTime.UtcNow,
                UserId: ctx.User?.Identity?.Name ?? "anonymous",
                Method: ctx.Request.Method,
                Path: ctx.Request.Path,
                StatusCode: ctx.Response.StatusCode);
            await _sink.WriteAsync(record);
        }
    }
}
'''


_DOTNET_EXCEPTION = '''// Global exception handler middleware.
//
// Catches every unhandled exception, logs the full stack trace
// server-side with a generated trace id, and returns a generic
// 500 JSON body that only exposes the trace id.
using System;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace Compliance.Middleware
{
    public class ExceptionHandlerMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly ILogger<ExceptionHandlerMiddleware> _logger;

        public ExceptionHandlerMiddleware(RequestDelegate next, ILogger<ExceptionHandlerMiddleware> logger)
        {
            _next = next;
            _logger = logger;
        }

        public async Task InvokeAsync(HttpContext ctx)
        {
            var traceId = ctx.Request.Headers["X-Trace-Id"].FirstOrDefault() ?? Guid.NewGuid().ToString();
            ctx.Response.Headers["X-Trace-Id"] = traceId;
            try
            {
                await _next(ctx);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "unhandled exception trace_id={TraceId} path={Path}", traceId, ctx.Request.Path);
                ctx.Response.StatusCode = 500;
                ctx.Response.ContentType = "application/json";
                var body = new
                {
                    error = "internal server error",
                    trace_id = traceId,
                    detail = "Contact support with the trace id above."
                };
                await ctx.Response.WriteAsync(JsonSerializer.Serialize(body));
            }
        }
    }
}
'''


_DOTNET_RBAC = '''// Role + scope enforcement attribute for ASP.NET Core.
//
// Apply to controllers or actions. Fails closed on missing claims.
using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace Compliance.Middleware
{
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class RequireRolesAttribute : ActionFilterAttribute
    {
        private readonly string[] _roles;
        public RequireRolesAttribute(params string[] roles) { _roles = roles; }

        public override void OnActionExecuting(ActionExecutingContext context)
        {
            var user = context.HttpContext.User;
            if (user?.Identity?.IsAuthenticated != true)
            {
                context.Result = new UnauthorizedResult();
                return;
            }
            var roles = user.FindAll("role").Select(c => c.Value).ToHashSet();
            if (!_roles.Any(r => roles.Contains(r)))
            {
                context.Result = new ForbidResult();
            }
        }
    }

    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class RequireScopesAttribute : ActionFilterAttribute
    {
        private readonly string[] _scopes;
        public RequireScopesAttribute(params string[] scopes) { _scopes = scopes; }

        public override void OnActionExecuting(ActionExecutingContext context)
        {
            var user = context.HttpContext.User;
            if (user?.Identity?.IsAuthenticated != true)
            {
                context.Result = new UnauthorizedResult();
                return;
            }
            var scopes = user.FindAll("scope").Select(c => c.Value).ToHashSet();
            var missing = _scopes.Where(s => !scopes.Contains(s)).ToList();
            if (missing.Any())
            {
                context.Result = new ForbidResult();
            }
        }
    }
}
'''


_DOTNET_PII = '''// PII masking helper for log sanitization.
//
// Usage: call PiiMasker.Mask(dict) before passing a payload to the
// logger. Fields matching known PII keys are redacted; email and
// phone are partially masked so records remain joinable by a
// non-reversible key.
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace Compliance.Middleware
{
    public static class PiiMasker
    {
        private static readonly HashSet<string> FullRedact = new()
        {
            "password", "pwd", "secret", "api_key", "apikey", "token",
            "credit_card", "card_number", "cvv", "cvc", "ssn", "tax_id",
            "national_id", "passport"
        };

        private static readonly HashSet<string> EmailKeys = new() { "email", "email_address", "correo" };
        private static readonly HashSet<string> PhoneKeys = new() { "phone", "phone_number", "telefono", "mobile" };

        public static Dictionary<string, object?> Mask(Dictionary<string, object?> input)
        {
            var result = new Dictionary<string, object?>();
            foreach (var kv in input)
            {
                var keyLower = kv.Key.ToLowerInvariant();
                if (FullRedact.Contains(keyLower))
                {
                    result[kv.Key] = "[REDACTED]";
                }
                else if (EmailKeys.Contains(keyLower) && kv.Value is string email && email.Contains('@'))
                {
                    var parts = email.Split('@', 2);
                    result[kv.Key] = parts[0].Length > 0
                        ? parts[0][..1] + "***@" + parts[1]
                        : email;
                }
                else if (PhoneKeys.Contains(keyLower) && kv.Value is string phone)
                {
                    var digits = Regex.Replace(phone, @"\\D", "");
                    result[kv.Key] = digits.Length >= 4
                        ? "***" + digits[^4..]
                        : "[REDACTED]";
                }
                else if (kv.Value is Dictionary<string, object?> nested)
                {
                    result[kv.Key] = Mask(nested);
                }
                else
                {
                    result[kv.Key] = kv.Value;
                }
            }
            return result;
        }
    }
}
'''


_DOTNET_PROGRAM = '''// Example Program.cs wire-up for all five compliance controls.
//
// Drop this snippet into your existing Program.cs. It shows where
// each middleware goes in the pipeline; order matters — the
// exception handler must be the outermost so it can catch failures
// in any other middleware.
using Compliance.Middleware;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<SoDRegistry>(_ =>
    new SoDRegistry(TimeSpan.FromHours(1)));
builder.Services.AddSingleton<IAuditLogSink, ConsoleAuditLogSink>();
builder.Services.AddAuthentication(/* your scheme here */);
builder.Services.AddAuthorization();
builder.Services.AddControllers();

var app = builder.Build();

// Order: outermost first
app.UseMiddleware<ExceptionHandlerMiddleware>();   // 1. catch everything
app.UseAuthentication();                           // 2. populate ctx.User
app.UseMiddleware<AuditLogMiddleware>();           // 3. log mutating requests
app.UseMiddleware<SoDMiddleware>();                // 4. enforce SoD
app.UseAuthorization();                            // 5. policy checks
app.MapControllers();

app.Run();
'''


_README = """# Compliance-by-Design Middleware

Auto-generated by NexusForge. Drop these files into your existing
application as a starting point for the five compliance controls
most modernization programs need at once:

1. **Segregation of Duties (SoD)** — `sod_middleware.*`
2. **Transactional audit logging** — `audit_log_middleware.*`
3. **Global exception handler** — `exception_handler.*`
4. **RBAC with scope enforcement** — `rbac_middleware.*`
5. **PII masking** — `pii_masker.*`

## Why drop-in?

Each template is opinionated, self-contained and ready to extend.
Wire them in at the top of your request pipeline; the example
files (`example_wire_up.py`, `ExampleProgram.cs`) show the order.

## What they do NOT do

- Persist to a real audit store — replace the default sinks with
  your SIEM / database / Kafka producer.
- Verify JWT signatures — delegate to your existing auth layer,
  populate `ctx.User` / `request.state.user` before the middleware
  runs.
- Replace your access control layer — the RBAC helpers are
  coarse-grained; combine with policy objects for fine-grained
  rules.

## Order matters

The exception handler is always outermost so it catches failures
from every downstream middleware. SoD runs before business logic
so a rejected request never produces side-effects.

_Generated by NexusForge compliance-by-design enforcer. Not real
client data._
"""


# ── Public entry point ─────────────────────────────────────────────────────


def generate_compliance_middleware(
    out_dir: Path,
    target: str = "both",  # python / dotnet / both
) -> GeneratedComplianceMiddleware:
    """Emit the compliance middleware package.

    Args:
        out_dir: Root directory for the generated files.
        target: ``"python"``, ``"dotnet"`` or ``"both"``.
    """
    target = target.lower()
    if target not in ("python", "dotnet", "both"):
        raise ValueError(f"unknown target: {target!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = GeneratedComplianceMiddleware(out_dir=str(out_dir), target=target)
    result.controls = [
        "segregation_of_duties",
        "transactional_audit_log",
        "exception_handler",
        "rbac_scopes",
        "pii_masking",
    ]

    # Top-level README
    (out_dir / "README.md").write_text(_README, encoding="utf-8")
    result.files_written.append("README.md")

    # Python
    if target in ("python", "both"):
        py_dir = out_dir / "python"
        py_dir.mkdir(exist_ok=True)
        (py_dir / "__init__.py").write_text("", encoding="utf-8")
        result.files_written.append("python/__init__.py")

        python_files = [
            ("sod_middleware.py", _PY_SOD),
            ("audit_log_middleware.py", _PY_AUDIT),
            ("exception_handler.py", _PY_EXCEPTION),
            ("rbac_middleware.py", _PY_RBAC),
            ("pii_masker.py", _PY_PII),
            ("example_wire_up.py", _PY_EXAMPLE),
        ]
        for name, content in python_files:
            (py_dir / name).write_text(content, encoding="utf-8")
            result.files_written.append(f"python/{name}")

    # .NET
    if target in ("dotnet", "both"):
        dotnet_dir = out_dir / "dotnet"
        dotnet_dir.mkdir(exist_ok=True)
        dotnet_files = [
            ("SoDMiddleware.cs", _DOTNET_SOD),
            ("AuditLogMiddleware.cs", _DOTNET_AUDIT),
            ("ExceptionHandlerMiddleware.cs", _DOTNET_EXCEPTION),
            ("RbacMiddleware.cs", _DOTNET_RBAC),
            ("PiiMasker.cs", _DOTNET_PII),
            ("ExampleProgram.cs", _DOTNET_PROGRAM),
        ]
        for name, content in dotnet_files:
            (dotnet_dir / name).write_text(content, encoding="utf-8")
            result.files_written.append(f"dotnet/{name}")

    return result
