"""Exponential backoff with jitter for step retries."""

import asyncio
import random

class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def should_retry(self, attempt: int, error: Exception) -> bool:
        if attempt >= self.max_retries:
            return False
        # Don't retry on validation/auth errors
        error_str = str(error).lower()
        if any(word in error_str for word in ["validation", "unauthorized", "forbidden", "invalid"]):
            return False
        return True

    async def wait(self, attempt: int):
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, delay * 0.3)
        await asyncio.sleep(delay + jitter)

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
