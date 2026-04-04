"""Pydantic v2 schemas for structured agent output validation.

Every agent that returns LLM-generated JSON should validate it against
these schemas.  On validation failure the agent can retry the LLM call
or fall back to a safe default.
"""

from pydantic import BaseModel, Field


# --- ExtractorAgent ---
class ExtractedEntity(BaseModel):
    type: str = Field(description="Entity type: person, organization, date, amount, location")
    value: str = Field(description="The extracted value")
    context: str = Field(default="", description="Sentence where the entity was found")


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


# --- SummarizerAgent ---
class SummaryResult(BaseModel):
    summary: str = Field(description="The concise summary text")
    key_points: list[str] = Field(default_factory=list)
    word_count: int = Field(default=0, ge=0)


# --- ValidatorAgent ---
class ValidationResult(BaseModel):
    is_valid: bool = Field(default=False)
    score: int = Field(default=0, ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# --- ClassifierAgent ---
class ClassificationResult(BaseModel):
    category: str = Field(description="One of the valid categories")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


# --- SentimentAgent ---
class SentimentResult(BaseModel):
    sentiment: str = Field(description="positive, negative, or neutral")
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
    emotions: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


# --- ScraperAgent ---
class ScrapingResult(BaseModel):
    extracted_data: dict = Field(default_factory=dict)
    source_url: str = Field(default="")
    fields_found: int = Field(default=0, ge=0)
    timestamp: str = Field(default="")
