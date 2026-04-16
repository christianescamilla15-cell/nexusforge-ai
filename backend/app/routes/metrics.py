"""Metrics endpoints — serves cost, token, and provider data from PostgreSQL."""

import json
import logging
import os
from fastapi import APIRouter
from app.observability.metrics import collector

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/metrics/summary')
async def get_metrics():
    return collector.get_summary()


@router.get('/reliability/health')
async def get_reliability_health():
    """System health with per-agent breakdown — reads from PostgreSQL."""
    try:
        from app.db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(AVG(processing_time_ms), 0) as avg_latency
                FROM pipeline_runs
            """)

            agent_rows = await conn.fetch("""
                SELECT agents_used, total_tokens, cost_usd, processing_time_ms, status
                FROM pipeline_runs WHERE agents_used IS NOT NULL
            """)

        agent_map = {}
        for row in agent_rows:
            agents = row["agents_used"]
            if isinstance(agents, str):
                agents = json.loads(agents)
            if not isinstance(agents, list):
                continue
            for name in agents:
                if name not in agent_map:
                    agent_map[name] = {"agent": name, "executions": 0, "tokens": 0,
                                       "retries": 0, "fallbacks": 0, "_lat": 0, "_ok": 0}
                a = agent_map[name]
                a["executions"] += 1
                a["tokens"] += row["total_tokens"] or 0
                a["_lat"] += row["processing_time_ms"] or 0
                if row["status"] == "completed":
                    a["_ok"] += 1

        agents = []
        for a in agent_map.values():
            agents.append({
                "agent": a["agent"],
                "executions": a["executions"],
                "avg_latency_ms": round(a["_lat"] / max(a["executions"], 1), 1),
                "tokens": a["tokens"],
                "retries": a["retries"],
                "fallbacks": a["fallbacks"],
                "success_rate": round(a["_ok"] / max(a["executions"], 1), 2),
            })

        total = stats["total_runs"] or 0
        ok = stats["successful"] or 0
        failed = stats["failed"] or 0

        return {
            "status": "healthy" if total > 0 and failed / max(total, 1) < 0.3 else "degraded",
            "total_runs": total,
            "successful_runs": ok,
            "failed_runs": failed,
            "system_success_rate": round(ok / max(total, 1), 3),
            "total_agents_tracked": len(agents),
            "avg_latency_ms": round(float(stats["avg_latency"] or 0), 1),
            "total_tokens": int(stats["total_tokens"] or 0),
            "total_cost": round(float(stats["total_cost"] or 0), 6),
            "agents": sorted(agents, key=lambda x: x["executions"], reverse=True),
        }
    except Exception as e:
        logger.warning("reliability/health from DB failed: %s", e)
        from app.metrics.reliability import get_system_health
        return get_system_health()


@router.get('/providers/status')
async def get_providers_status():
    """Active LLM provider status."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    active = "groq" if groq_key else ("anthropic" if anthropic_key else "none")

    return {
        "active_provider": active,
        "groq": {
            "configured": bool(groq_key),
            "model": "llama-3.3-70b-versatile",
            "role": "primary",
        },
        "anthropic": {
            "configured": bool(anthropic_key),
            "model": "claude-sonnet-4-6",
            "role": "fallback",
        },
    }
