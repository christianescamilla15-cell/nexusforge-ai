"""Multi-provider LLM router with circuit breaker."""

import time
import logging
from collections import deque

from app.llm.provider import LLMResponse
from app.llm.groq_provider import GroqProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.token_tracker import calculate_cost

logger = logging.getLogger(__name__)

# Circuit breaker settings
_CB_ERROR_THRESHOLD = 3      # errors to trigger open circuit
_CB_WINDOW_SECONDS = 60      # window to count errors in
_CB_COOLDOWN_SECONDS = 30    # how long to skip a tripped provider


class _CircuitBreaker:
    """Simple circuit breaker per provider."""

    def __init__(self):
        self._errors: deque[float] = deque()
        self._open_until: float = 0.0

    def record_error(self):
        now = time.monotonic()
        self._errors.append(now)
        # Purge old entries
        cutoff = now - _CB_WINDOW_SECONDS
        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()
        # Trip if threshold reached
        if len(self._errors) >= _CB_ERROR_THRESHOLD:
            self._open_until = now + _CB_COOLDOWN_SECONDS
            logger.warning("Circuit breaker tripped — cooldown %ds", _CB_COOLDOWN_SECONDS)

    def is_open(self) -> bool:
        if time.monotonic() < self._open_until:
            return True
        return False

    def reset(self):
        self._errors.clear()
        self._open_until = 0.0


class LLMRouter:
    """Route LLM calls through available providers with failover."""

    def __init__(self):
        self._providers = [GroqProvider(), ClaudeProvider()]
        self._breakers: dict[str, _CircuitBreaker] = {
            p.name: _CircuitBreaker() for p in self._providers
        }

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048) -> LLMResponse:
        """Try providers in order: Groq first, then Claude. Respects circuit breakers."""
        errors = []

        for provider in self._providers:
            if not provider.is_available():
                continue
            breaker = self._breakers[provider.name]
            if breaker.is_open():
                logger.info("Skipping %s (circuit open)", provider.name)
                continue

            try:
                response = await provider.chat(messages, temperature, max_tokens)
                breaker.reset()
                # Attach cost
                response.cost_usd = calculate_cost(
                    response.provider, response.tokens_input, response.tokens_output
                )
                return response
            except Exception as exc:
                logger.warning("Provider %s failed: %s", provider.name, exc)
                breaker.record_error()
                errors.append((provider.name, exc))

        # All providers exhausted
        detail = "; ".join(f"{n}: {e}" for n, e in errors)
        raise RuntimeError(f"All LLM providers failed — {detail}" if detail else "No LLM providers available")


# Module-level singleton
_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
