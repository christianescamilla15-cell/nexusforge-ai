import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


async def _voyage_embedding(text: str) -> list[float]:
    """Get embedding from Voyage AI (cloud, 512d)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            VOYAGE_URL,
            headers={
                "Authorization": f"Bearer {settings.voyage_api_key}",
                "Content-Type": "application/json",
            },
            json={"input": [text], "model": "voyage-3-lite"},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


async def _ollama_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text (local, 768d)."""
    ollama_url = getattr(settings, "ollama_url", "http://localhost:11434")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ollama_url}/api/embed",
            json={"model": "nomic-embed-text", "input": text},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        # Ollama returns {"embeddings": [[...]]}
        return data["embeddings"][0]


async def get_embedding(text: str) -> list[float]:
    """Get embedding with fallback: Voyage AI → Ollama nomic-embed-text."""
    # Try Voyage AI first if key is configured
    if getattr(settings, "voyage_api_key", None):
        try:
            return await _voyage_embedding(text)
        except Exception as exc:
            logger.warning("Voyage AI embedding failed, falling back to Ollama: %s", exc)

    # Fallback to local Ollama
    try:
        return await _ollama_embedding(text)
    except Exception as exc:
        logger.warning("Ollama embedding also failed: %s", exc)
        raise


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding with fallback chain."""
    # Try Voyage AI first
    if getattr(settings, "voyage_api_key", None):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    VOYAGE_URL,
                    headers={
                        "Authorization": f"Bearer {settings.voyage_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": texts, "model": "voyage-3-lite"},
                    timeout=30.0,
                )
                response.raise_for_status()
                return [item["embedding"] for item in response.json()["data"]]
        except Exception as exc:
            logger.warning("Voyage AI batch failed, falling back to Ollama: %s", exc)

    # Fallback: individual Ollama calls
    results = []
    for text in texts:
        emb = await _ollama_embedding(text)
        results.append(emb)
    return results
