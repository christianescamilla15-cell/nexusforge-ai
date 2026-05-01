"""HTTP routes for the Platform Synthesizer.

Three endpoints:
  - POST /platform-synth/chat    — one chat turn (extract spec + suggestions)
  - GET  /platform-synth/templates — list registered templates
  - POST /platform-synth/build   — finalize spec + template, write to disk

Auth: all endpoints require a valid JWT (per app's standard
middleware). The synthesizer deliberately does NOT cross-tenant —
each user can only generate to a path under the configured root,
and the build endpoint records the actor for audit.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.auth.jwt_handler import verify_token
from app.platform_synth import chat as chat_module
from app.platform_synth.schemas import (
    BuildRequest,
    BuildResult,
    ChatTurnInput,
    ChatTurnOutput,
)
from app.platform_synth.synthesizer import synthesize
from app.platform_synth.templates import list_templates

router = APIRouter(prefix="/platform-synth", tags=["platform-synth"])
logger = logging.getLogger(__name__)


def _require_user(request: Request) -> str:
    """Verify JWT and return user_id. Raises 401 if missing/invalid.

    Mirrors the pattern used elsewhere in the codebase
    (e.g., routes/workflows.py:_get_user_id).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid or expired token")
    return token_data["sub"]


@router.post("/chat", response_model=ChatTurnOutput)
async def chat_turn(body: ChatTurnInput, request: Request):
    """One conversation round — Claude extracts spec + ranks templates."""
    _require_user(request)
    try:
        return await chat_module.run_chat_turn(body)
    except Exception as exc:
        logger.exception("platform-synth chat turn failed")
        raise HTTPException(500, "Chat turn failed; see logs")


@router.get("/templates")
async def list_available_templates(request: Request):
    """Return all registered template summaries.

    Used by the frontend to populate the suggestion panel even
    before the user has chatted (so they see options up front).
    """
    _require_user(request)
    return {"templates": [t.model_dump() for t in list_templates()]}


@router.post("/build", response_model=BuildResult)
async def build_project(body: BuildRequest, request: Request):
    """Generate the project on disk.

    The user-supplied `target_dir` is validated server-side: must
    live under `PLATFORM_SYNTH_ROOT` (default `~/nexusforge-generated`)
    and must be empty/non-existent.
    """
    user_id = _require_user(request)
    try:
        result = synthesize(body)
        logger.info(
            "platform-synth build by %s: template=%s path=%s files=%d",
            user_id[:8], body.template_id, result.project_path, result.files_written,
        )
        return result
    except KeyError:
        raise HTTPException(404, f"Unknown template: {body.template_id}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception:
        logger.exception("platform-synth build failed")
        raise HTTPException(500, "Build failed; see logs")
