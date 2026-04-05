"""Post-execution output dispatcher — sends results to configured destinations.

Reads `output_config` from the automation and dispatches to each enabled destination
using the global integration credentials already configured by the user.

Usage:
    await dispatch_outputs(automation_id, run_id, user_id, result_summary)
"""

import json
import logging
from uuid import UUID

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


async def dispatch_outputs(
    automation_id: UUID,
    run_id: UUID,
    user_id: str,
    result_summary: dict,
) -> dict:
    """Dispatch results to all enabled output destinations for this automation.

    Args:
        automation_id: The automation that ran
        run_id: The workflow_run ID
        user_id: Owner of the automation
        result_summary: Dict with keys like workflow_name, status, total_tokens, cost_usd, agents_used, summary

    Returns:
        Dict with dispatch results per destination
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT output_config, name FROM automations WHERE id = $1",
            automation_id,
        )

    if not row:
        return {"skipped": "automation not found"}

    config = row["output_config"] or {}
    if isinstance(config, str):
        config = json.loads(config)

    if not config:
        return {"skipped": "no output_config set"}

    auto_name = row["name"] or "Automation"
    results = {}

    # Email
    if config.get("email"):
        try:
            from app.integrations.email.notify import notify_workflow_complete
            sent = await notify_workflow_complete(
                workflow_name=auto_name,
                status=result_summary.get("status", "completed"),
                summary=result_summary.get("summary", "Execution completed"),
                agents_used=result_summary.get("agents_used", []),
                total_tokens=result_summary.get("total_tokens", 0),
                cost_usd=result_summary.get("cost_usd", 0),
                processing_time_ms=result_summary.get("processing_time_ms", 0),
            )
            results["email"] = "sent" if sent else "failed"
        except Exception as e:
            logger.warning("output_dispatch email failed: %s", e)
            results["email"] = f"error: {e}"

    # Slack
    if config.get("slack"):
        try:
            from app.integrations.slack.client import notify_slack
            sent = await notify_slack(
                user_id=user_id,
                event_type="execution_complete",
                workflow_name=auto_name,
                status=result_summary.get("status", "completed"),
                tokens=result_summary.get("total_tokens", 0),
                cost=result_summary.get("cost_usd", 0),
                agents_used=result_summary.get("agents_used", []),
                summary=result_summary.get("summary", ""),
            )
            results["slack"] = "sent" if sent else "not_configured"
        except Exception as e:
            logger.warning("output_dispatch slack failed: %s", e)
            results["slack"] = f"error: {e}"

    # Notion
    if config.get("notion"):
        try:
            from app.integrations.notion.client import create_page
            page = await create_page(
                user_id=user_id,
                title=f"{auto_name} — Run {str(run_id)[:8]}",
                content=result_summary.get("summary", "Execution completed"),
                metadata={
                    "status": result_summary.get("status"),
                    "tokens": result_summary.get("total_tokens", 0),
                    "cost": result_summary.get("cost_usd", 0),
                },
            )
            results["notion"] = "created" if page else "failed"
        except Exception as e:
            logger.warning("output_dispatch notion failed: %s", e)
            results["notion"] = f"error: {e}"

    # Google Drive
    if config.get("drive"):
        try:
            from app.integrations.google_drive.client import create_file
            folder_id = config.get("drive_folder_id", "1P56v2fkzWZbgEFSqhQvZsQPu9x8_1vb6")
            uploaded = await create_file(
                name=f"{auto_name}_run_{str(run_id)[:8]}.json",
                content=json.dumps(result_summary, indent=2, default=str),
                folder_id=folder_id,
                mime_type="application/json",
            )
            results["drive"] = "uploaded" if uploaded.get("status") == "success" else f"failed: {uploaded.get('message', '')}"
        except Exception as e:
            logger.warning("output_dispatch drive failed: %s", e)
            results["drive"] = f"error: {e}"

    # Webhook
    if config.get("webhook"):
        try:
            import httpx
            webhook_url = config.get("webhook_url", "")
            if webhook_url:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(webhook_url, json={
                        "automation": auto_name,
                        "run_id": str(run_id),
                        **result_summary,
                    })
                    results["webhook"] = f"sent ({resp.status_code})"
            else:
                results["webhook"] = "no_url"
        except Exception as e:
            logger.warning("output_dispatch webhook failed: %s", e)
            results["webhook"] = f"error: {e}"

    logger.info("output_dispatch for %s: %s", auto_name, results)
    return results
