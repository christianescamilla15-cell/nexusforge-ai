"""Public demo endpoint — rate-limited, no auth required."""
import time
import logging
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/demo", tags=["demo"])
logger = logging.getLogger(__name__)

# Simple in-memory rate limiter: {ip: [timestamps]}
_demo_calls: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 5  # max calls
RATE_WINDOW = 3600  # per hour (seconds)


def _check_rate_limit(ip: str) -> bool:
    """Return True if allowed, False if rate-limited."""
    now = time.time()
    # Prune old entries
    _demo_calls[ip] = [t for t in _demo_calls[ip] if now - t < RATE_WINDOW]
    if len(_demo_calls[ip]) >= RATE_LIMIT:
        return False
    _demo_calls[ip].append(now)
    return True


@router.post("/analyze")
async def demo_analyze(body: dict, request: Request):
    """Analyze text without auth — rate limited to 5 calls per IP per hour."""
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(429, "Rate limit exceeded. Max 5 demo analyses per hour.")

    text = body.get("text", "")
    if not text or len(text) < 10:
        raise HTTPException(400, "Text must be at least 10 characters")
    if len(text) > 2000:
        raise HTTPException(400, "Text must be under 2000 characters for demo")

    try:
        from app.use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
        from app.use_cases.enterprise_ops.schemas import OperationsRequest

        result = await run_enterprise_ops_workflow(
            OperationsRequest(message=text[:2000])
        )
        return {
            "intent": result.intent,
            "classification": result.intent,
            "urgency": _infer_urgency(result.intent, text),
            "customer_name": result.customer_name,
            "entities": list(filter(None, [result.customer_name] + (result.actions_taken or [])[:3])),
            "summary": result.response_message[:300] if result.response_message else "",
            "suggested_response": result.response_message,
            "agents_used": result.agents_used,
            "processing_time_ms": result.processing_time_ms,
            "tokens_used": result.total_tokens,
        }
    except Exception as exc:
        logger.exception("Demo analysis failed")
        raise HTTPException(500, f"Analysis failed: {str(exc)}")


def _infer_urgency(intent: str, text: str) -> str:
    """Simple urgency inference for demo purposes."""
    text_lower = text.lower()
    high_keywords = ["urgente", "urgent", "emergencia", "emergency", "inmediato", "asap", "critical"]
    if any(kw in text_lower for kw in high_keywords):
        return "high"
    medium_keywords = ["pronto", "soon", "importante", "important", "necesito", "need"]
    if any(kw in text_lower for kw in medium_keywords):
        return "medium"
    if intent in ("reschedule_meeting", "order_issue", "complaint"):
        return "medium"
    return "low"
