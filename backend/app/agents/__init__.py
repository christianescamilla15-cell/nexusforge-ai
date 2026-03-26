"""Auto-register all agents on import."""

from app.agents import (  # noqa: F401
    classifier,
    extractor,
    summarizer,
    analyzer,
    enricher,
    validator,
    reporter,
    repair,
)
