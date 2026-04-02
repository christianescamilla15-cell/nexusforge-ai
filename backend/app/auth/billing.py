"""Stripe billing — subscription management for NexusForge plans."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..db.client import get_db_pool
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs (configure in env for production)
PLAN_PRICES = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", ""),
    "team": os.environ.get("STRIPE_PRICE_TEAM", ""),
}


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, request: Request):
    """Create Stripe Checkout session for plan upgrade."""
    if not STRIPE_SECRET:
        raise HTTPException(503, "Billing not configured")

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    if req.plan not in PLAN_PRICES or not PLAN_PRICES[req.plan]:
        raise HTTPException(400, f"Invalid plan: {req.plan}")

    import stripe
    stripe.api_key = STRIPE_SECRET

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE id = $1::uuid", token_data["sub"])

    if not user:
        raise HTTPException(404, "User not found")

    # Create or get Stripe customer
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            name=user["name"],
            metadata={"nexusforge_user_id": str(user["id"])},
        )
        customer_id = customer.id
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE nf_users SET stripe_customer_id = $1 WHERE id = $2::uuid",
                customer_id, str(user["id"]),
            )

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": PLAN_PRICES[req.plan], "quantity": 1}],
        metadata={"user_id": str(user["id"]), "plan": req.plan},
        success_url=os.environ.get("FRONTEND_URL", "https://frontend-silk-three-66.vercel.app") + "/settings?billing=success",
        cancel_url=os.environ.get("FRONTEND_URL", "https://frontend-silk-three-66.vercel.app") + "/settings?billing=cancel",
    )

    return {"url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe subscription events."""
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

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        subscription_id = session.get("subscription")

        if user_id and plan:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE nf_users SET plan = $1, stripe_subscription_id = $2 WHERE id = $3::uuid",
                    plan, subscription_id, user_id,
                )
            logger.info("User %s upgraded to %s", user_id, plan)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE nf_users SET plan = 'free', stripe_subscription_id = NULL WHERE stripe_customer_id = $1",
                customer_id,
            )
        logger.info("Subscription cancelled for customer %s", customer_id)

    return {"received": True}


@router.get("/status")
async def billing_status(request: Request):
    """Get current billing status for logged-in user."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT plan, runs_today, runs_reset_date, stripe_subscription_id FROM nf_users WHERE id = $1::uuid",
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
    }
