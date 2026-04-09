"""Token cost tracking for LLM providers."""

# Pricing per million tokens (USD)
PRICING = {
    "ollama": {
        "input": 0.0,   # local inference, no cost
        "output": 0.0,
    },
    "groq": {
        "input": 0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    },
    "claude": {
        "input": 3.0 / 1_000_000,   # Sonnet 4.6
        "output": 15.0 / 1_000_000,
    },
    "haiku": {
        "input": 1.0 / 1_000_000,   # Haiku 4.5 — 5x cheaper than Sonnet
        "output": 5.0 / 1_000_000,
    },
    "openai": {
        "input": 0.15 / 1_000_000,   # GPT-4o-mini
        "output": 0.60 / 1_000_000,
    },
    "openai-gpt4o": {
        "input": 2.50 / 1_000_000,   # GPT-4o
        "output": 10.0 / 1_000_000,
    },
}


def calculate_cost(provider: str, tokens_input: int, tokens_output: int) -> float:
    """Calculate USD cost for a request given provider and token counts."""
    rates = PRICING.get(provider, {"input": 0.0, "output": 0.0})
    return (tokens_input * rates["input"]) + (tokens_output * rates["output"])
