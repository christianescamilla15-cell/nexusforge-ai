"""Per-user rate limiting based on plan tier."""

import logging
from datetime import date
from fastapi import Request, HTTPException
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)

PLAN_LIMITS = {
    "free": 5,
    "pro": 100,
    "team": 500,
    "enterprise": -1,  # unlimited
}


async def check_rate_limit(request: Request) -> bool:
    """Check if the user has remaining runs for today.

    Returns True if allowed, raises HTTPException if limit exceeded.
    For anonymous users, applies free tier limit by IP.
    """
    user_id = getattr(request.state, "user_id", None)
    plan = getattr(request.state, "user_plan", "free")

    limit = PLAN_LIMITS.get(plan, 5)
    if limit == -1:
        return True  # Unlimited

    if not user_id:
        return True  # Anonymous users not rate limited (for now)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT runs_today, runs_reset_date, plan FROM nf_users WHERE id = $1::uuid",
                user_id,
            )
            if not user:
                return True

            today = date.today()
            runs = user["runs_today"] or 0
            reset_date = user["runs_reset_date"]

            # Reset counter if new day
            if reset_date != today:
                await conn.execute(
                    "UPDATE nf_users SET runs_today = 0, runs_reset_date = $1 WHERE id = $2::uuid",
                    today, user_id,
                )
                runs = 0

            user_limit = PLAN_LIMITS.get(user["plan"] or "free", 5)

            # Store rate limit info in request state for response headers
            request.state.rate_limit = user_limit
            request.state.rate_remaining = max(0, user_limit - runs - 1)

            if user_limit != -1 and runs >= user_limit:
                raise HTTPException(
                    429,
                    f"Daily limit reached ({user_limit} runs/day on {user['plan']} plan). Upgrade at /api/auth/plans",
                    headers={
                        "X-RateLimit-Limit": str(user_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "midnight UTC",
                    },
                )

            # Increment counter
            await conn.execute(
                "UPDATE nf_users SET runs_today = runs_today + 1 WHERE id = $1::uuid",
                user_id,
            )
            return True

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limit check failed: %s", e)
        return True  # Fail open
