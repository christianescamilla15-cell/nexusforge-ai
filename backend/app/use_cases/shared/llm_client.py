"""
Shared LLM client for use cases.
Uses Groq as primary (free tier), falls back to rule-based logic.
"""
import os
import time
import httpx

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _get_groq_key():
    """Read key at call time, not import time (important for serverless)."""
    return os.environ.get("GROQ_API_KEY", "")


async def llm_generate(prompt: str, system: str = "", max_tokens: int = 300) -> dict:
    """Call Groq LLM if available, return usage metadata."""
    GROQ_API_KEY = _get_groq_key()
    if not GROQ_API_KEY:
        return {
            "text": None,
            "provider": "none",
            "model": "none",
            "tokens_input": 0,
            "tokens_output": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": 0,
            "llm_used": False,
        }

    start = time.time()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            data = response.json()

        latency = round((time.time() - start) * 1000, 1)
        usage = data.get("usage", {})
        text = data["choices"][0]["message"]["content"]

        # Groq pricing: $0.59/M input, $0.79/M output
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        cost = (tokens_in * 0.00000059) + (tokens_out * 0.00000079)

        return {
            "text": text,
            "provider": "groq",
            "model": GROQ_MODEL,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "cost_usd": round(cost, 8),
            "latency_ms": latency,
            "llm_used": True,
        }
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {
            "text": None,
            "provider": "groq",
            "model": GROQ_MODEL,
            "tokens_input": 0,
            "tokens_output": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": latency,
            "llm_used": False,
            "error": str(e),
        }
