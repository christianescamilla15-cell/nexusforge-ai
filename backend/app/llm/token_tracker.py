"""Token cost tracking for LLM providers."""

# Pricing per million tokens (USD)
PRICING = {
    "groq": {
        "input": 0.59 / 1_000_000,
        "output": 0.79 / 1_000_000,
    },
    "claude": {
        "input": 3.0 / 1_000_000,
        "output": 15.0 / 1_000_000,
    },
}


def calculate_cost(provider: str, tokens_input: int, tokens_output: int) -> float:
    """Calculate USD cost for a request given provider and token counts."""
    rates = PRICING.get(provider, {"input": 0.0, "output": 0.0})
    return (tokens_input * rates["input"]) + (tokens_output * rates["output"])
