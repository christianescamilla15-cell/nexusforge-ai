import httpx
from app.config import settings

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


async def get_embedding(text: str) -> list[float]:
    """Get 512d embedding from Voyage AI."""
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


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding for multiple texts."""
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
