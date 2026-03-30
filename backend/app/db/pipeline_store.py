"""Persist pipeline run results to PostgreSQL."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def save_pipeline_run(
    pool,
    pipeline_name: str,
    status: str,
    trigger_source: str = "backend",
    file_name: Optional[str] = None,
    document_type: Optional[str] = None,
    input_summary: Optional[dict] = None,
    output_summary: Optional[dict] = None,
    steps: Optional[list] = None,
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    processing_time_ms: Optional[int] = None,
    llm_used: bool = False,
    agents_used: Optional[list] = None,
    notion_url: Optional[str] = None,
    webhook_sent: bool = False,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """Insert a pipeline run record. Returns run ID or None on failure."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO pipeline_runs
                   (pipeline_name, status, trigger_source, input_summary, output_summary,
                    steps, file_name, document_type, total_tokens, cost_usd,
                    processing_time_ms, llm_used, agents_used, notion_url,
                    webhook_sent, error_message)
                   VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8, $9, $10,
                           $11, $12, $13::jsonb, $14, $15, $16)
                   RETURNING id""",
                pipeline_name,
                status,
                trigger_source,
                json.dumps(input_summary or {}),
                json.dumps(output_summary or {}),
                json.dumps(steps or []),
                file_name,
                document_type,
                total_tokens,
                cost_usd,
                processing_time_ms,
                llm_used,
                json.dumps(agents_used or []),
                notion_url,
                webhook_sent,
                error_message,
            )
            run_id = str(row["id"])
            logger.info("Pipeline run saved: %s (%s)", run_id, pipeline_name)
            return run_id
    except Exception as exc:
        logger.warning("Failed to persist pipeline run: %s", exc)
        return None


async def list_pipeline_runs(pool, pipeline_name: Optional[str] = None, limit: int = 20) -> list:
    """List recent pipeline runs."""
    try:
        async with pool.acquire() as conn:
            if pipeline_name:
                rows = await conn.fetch(
                    """SELECT id, pipeline_name, status, trigger_source, file_name,
                              document_type, total_tokens, cost_usd, processing_time_ms,
                              llm_used, agents_used, notion_url, webhook_sent, steps,
                              error_message, created_at
                       FROM pipeline_runs
                       WHERE pipeline_name = $1
                       ORDER BY created_at DESC LIMIT $2""",
                    pipeline_name,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, pipeline_name, status, trigger_source, file_name,
                              document_type, total_tokens, cost_usd, processing_time_ms,
                              llm_used, agents_used, notion_url, webhook_sent, steps,
                              error_message, created_at
                       FROM pipeline_runs
                       ORDER BY created_at DESC LIMIT $1""",
                    limit,
                )
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Failed to list pipeline runs: %s", exc)
        return []
