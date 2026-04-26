"""Automation Templates — pre-built kits users can deploy with one click."""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter(prefix="/templates", tags=["templates"])
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("id",):
        if key in d and d[key] is not None:
            d[key] = str(d[key])
    # JSONB fields come as dicts already from asyncpg
    for key in ("dag_definition", "input_config", "default_rules", "suggested_connectors"):
        val = d.get(key)
        if isinstance(val, str):
            d[key] = json.loads(val)
    if "created_at" in d and d["created_at"]:
        d["created_at"] = d["created_at"].isoformat()
    return d


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_templates():
    """List all available automation templates."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, slug, name, description, icon, color, category,
                          dag_definition, input_config, default_rules,
                          suggested_connectors, estimated_agents, created_at
                   FROM automation_templates
                   ORDER BY category, name"""
            )
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        logger.exception("Failed to list templates")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{slug}")
async def get_template(slug: str):
    """Get a single template by slug."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, slug, name, description, icon, color, category,
                          dag_definition, input_config, default_rules,
                          suggested_connectors, estimated_agents, created_at
                   FROM automation_templates
                   WHERE slug = $1""",
                slug,
            )
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        return _row_to_dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get template")
        raise HTTPException(status_code=500, detail="Internal server error")


class DeployRequest(BaseModel):
    name_override: Optional[str] = None


@router.post("/{slug}/deploy", status_code=201)
async def deploy_template(slug: str, body: DeployRequest = DeployRequest(), request: Request = None):
    """Deploy a template: create workflow + automation + optional rules."""
    user_id = _get_user_id(request) if request else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Fetch template
            tpl = await conn.fetchrow(
                """SELECT slug, name, description, icon, color, category,
                          dag_definition, input_config, default_rules,
                          suggested_connectors, estimated_agents
                   FROM automation_templates WHERE slug = $1""",
                slug,
            )
            if not tpl:
                raise HTTPException(status_code=404, detail="Template not found")

            wf_name = body.name_override or tpl["name"]
            dag_def = tpl["dag_definition"]
            if isinstance(dag_def, str):
                dag_def = json.loads(dag_def)

            input_config = tpl["input_config"]
            if isinstance(input_config, str):
                input_config = json.loads(input_config)

            default_rules = tpl["default_rules"]
            if isinstance(default_rules, str):
                default_rules = json.loads(default_rules)

            # 2. Create workflow from dag_definition
            # C-2 (2026-04-25): set user_id on the workflow so it is owned
            # by the caller. Previously omitted → workflow row landed with
            # NULL user_id, which the `OR user_id IS NULL` reads across
            # the codebase exposed to every authenticated user.
            wf_row = await conn.fetchrow(
                """INSERT INTO workflows (name, description, dag_definition, status, user_id)
                   VALUES ($1, $2, $3::jsonb, 'active', $4::uuid)
                   RETURNING id""",
                wf_name,
                tpl["description"],
                json.dumps(dag_def),
                user_id,
            )
            workflow_id = wf_row["id"]

            # 3. Create automation linked to that workflow
            auto_row = await conn.fetchrow(
                """INSERT INTO automations
                       (user_id, workflow_id, name, description, icon, color,
                        trigger_type, input_config)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, 'manual', $7::jsonb)
                   RETURNING id, created_at""",
                user_id,
                workflow_id,
                wf_name,
                tpl["description"],
                tpl["icon"],
                tpl["color"],
                json.dumps(input_config),
            )
            automation_id = auto_row["id"]

            # 4. Create default rules if any
            rules_created = 0
            if default_rules:
                for i, rule in enumerate(default_rules):
                    await conn.execute(
                        """INSERT INTO automation_rules
                               (automation_id, name, description, priority, conditions, actions)
                           VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)""",
                        automation_id,
                        rule.get("name", f"Rule {i+1}"),
                        rule.get("description"),
                        i,
                        json.dumps(rule.get("conditions", [])),
                        json.dumps(rule.get("actions", [])),
                    )
                    rules_created += 1

        return {
            "automation_id": str(automation_id),
            "workflow_id": str(workflow_id),
            "rules_created": rules_created,
            "template_slug": slug,
            "created_at": auto_row["created_at"].isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to deploy template %s", slug)
        raise HTTPException(status_code=500, detail="Internal server error")
