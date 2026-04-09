"""Stripe billing — subscriptions + metered usage for NexusForge SaaS.

Features:
  - Plan-based subscriptions (free/pro/team/enterprise)
  - Metered billing: tokens consumed, runs executed, files processed
  - Usage dashboard per org
  - Stripe webhook handling (subscription + invoice events)
  - Organization-level billing (not individual user)
"""

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..db.client import get_db_pool
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://nexusforge-two.vercel.app")

PLAN_PRICES = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", ""),
    "team": os.environ.get("STRIPE_PRICE_TEAM", ""),
}

# Metered price IDs
METERED_PRICES = {
    "tokens": os.environ.get("STRIPE_METERED_TOKENS", ""),      # Per 1M tokens
    "runs": os.environ.get("STRIPE_METERED_RUNS", ""),           # Per execution run
    "files": os.environ.get("STRIPE_METERED_FILES", ""),         # Per file processed
}


def _get_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, "Invalid token")
    return data


class CheckoutRequest(BaseModel):
    plan: str
    org_id: str = ""  # Organization to upgrade


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, request: Request):
    """Create Stripe Checkout session for plan upgrade."""
    if not STRIPE_SECRET:
        raise HTTPException(503, "Billing not configured")

    token_data = _get_user(request)

    if req.plan not in PLAN_PRICES or not PLAN_PRICES[req.plan]:
        raise HTTPException(400, f"Invalid plan: {req.plan}")

    import stripe
    stripe.api_key = STRIPE_SECRET

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE id = $1::uuid", token_data["sub"])

    if not user:
        raise HTTPException(404, "User not found")

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            name=user["name"],
            metadata={"nexusforge_user_id": str(user["id"]), "org_id": req.org_id},
        )
        customer_id = customer.id
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE nf_users SET stripe_customer_id = $1 WHERE id = $2::uuid",
                customer_id, str(user["id"]),
            )

    # Build line items: subscription + metered components
    line_items = [{"price": PLAN_PRICES[req.plan], "quantity": 1}]

    # Add metered billing items if configured
    for meter_name, price_id in METERED_PRICES.items():
        if price_id:
            line_items.append({"price": price_id})

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=line_items,
        metadata={"user_id": str(user["id"]), "plan": req.plan, "org_id": req.org_id},
        success_url=f"{FRONTEND_URL}/settings?billing=success",
        cancel_url=f"{FRONTEND_URL}/settings?billing=cancel",
    )

    return {"url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe subscription and invoice events."""
    if not STRIPE_SECRET:
        return {"received": True}

    import stripe
    stripe.api_key = STRIPE_SECRET

    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        org_id = session.get("metadata", {}).get("org_id")
        subscription_id = session.get("subscription")

        if user_id and plan:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE nf_users SET plan = $1, stripe_subscription_id = $2 WHERE id = $3::uuid",
                    plan, subscription_id, user_id,
                )
                if org_id:
                    await conn.execute(
                        "UPDATE organizations SET plan = $1, stripe_subscription_id = $2 WHERE id = $3::uuid",
                        plan, subscription_id, org_id,
                    )
            logger.info("Plan upgraded: user=%s org=%s plan=%s", user_id[:8], org_id[:8] if org_id else "none", plan)

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE nf_users SET plan = 'free', stripe_subscription_id = NULL WHERE stripe_customer_id = $1",
                customer_id,
            )
            await conn.execute(
                "UPDATE organizations SET plan = 'free', stripe_subscription_id = NULL WHERE stripe_customer_id = $1",
                customer_id,
            )
        logger.info("Subscription cancelled: customer=%s", customer_id)

    return {"received": True}


@router.get("/status")
async def billing_status(request: Request):
    """Get billing status with usage breakdown."""
    token_data = _get_user(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT plan, runs_today, runs_reset_date, stripe_subscription_id FROM nf_users WHERE id = $1::uuid",
            token_data["sub"],
        )

        # Get usage stats for current period
        usage = await conn.fetchrow(
            """SELECT
                COALESCE(SUM(total_tokens), 0) AS tokens_used,
                COALESCE(SUM(total_cost_usd), 0) AS cost_usd,
                COUNT(*) AS total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs
               FROM workflow_runs
               WHERE user_id = $1::uuid AND created_at >= date_trunc('month', now())""",
            token_data["sub"],
        )

    if not user:
        raise HTTPException(404, "User not found")

    from .rate_limit import PLAN_LIMITS
    plan = user["plan"] or "free"
    limit = PLAN_LIMITS.get(plan, 5)

    return {
        "plan": plan,
        "runs_today": user["runs_today"] or 0,
        "runs_limit": limit if limit != -1 else "unlimited",
        "has_subscription": bool(user["stripe_subscription_id"]),
        "usage_this_month": {
            "tokens": int(usage["tokens_used"]) if usage else 0,
            "cost_usd": round(float(usage["cost_usd"]), 4) if usage else 0,
            "total_runs": int(usage["total_runs"]) if usage else 0,
            "completed": int(usage["completed_runs"]) if usage else 0,
            "failed": int(usage["failed_runs"]) if usage else 0,
        },
    }


@router.post("/report-usage")
async def report_usage(request: Request):
    """Report metered usage to Stripe (called after each execution)."""
    if not STRIPE_SECRET:
        return {"reported": False, "reason": "Billing not configured"}

    token_data = _get_user(request)
    body = await request.json()

    tokens = body.get("tokens", 0)
    runs = body.get("runs", 0)
    files = body.get("files", 0)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT stripe_subscription_id FROM nf_users WHERE id = $1::uuid",
            token_data["sub"],
        )

    if not user or not user["stripe_subscription_id"]:
        return {"reported": False, "reason": "No active subscription"}

    import stripe
    stripe.api_key = STRIPE_SECRET

    reported = {}
    try:
        sub = stripe.Subscription.retrieve(user["stripe_subscription_id"])
        for item in sub["items"]["data"]:
            price_id = item["price"]["id"]
            if price_id == METERED_PRICES.get("tokens") and tokens > 0:
                stripe.SubscriptionItem.create_usage_record(
                    item["id"], quantity=max(1, tokens // 1000), timestamp=int(time.time()),
                )
                reported["tokens"] = tokens
            elif price_id == METERED_PRICES.get("runs") and runs > 0:
                stripe.SubscriptionItem.create_usage_record(
                    item["id"], quantity=runs, timestamp=int(time.time()),
                )
                reported["runs"] = runs
            elif price_id == METERED_PRICES.get("files") and files > 0:
                stripe.SubscriptionItem.create_usage_record(
                    item["id"], quantity=files, timestamp=int(time.time()),
                )
                reported["files"] = files
    except Exception as exc:
        logger.warning("Usage report failed: %s", exc)
        return {"reported": False, "reason": "Stripe error"}

    return {"reported": True, "usage": reported}
