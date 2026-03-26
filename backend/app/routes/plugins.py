"""Plugin management endpoints."""

from fastapi import APIRouter
from app.plugins.loader import list_plugins

router = APIRouter()


@router.get("/")
async def get_plugins():
    """Return all loaded plugins with their manifests."""
    plugins = list_plugins()
    return {
        "total": len(plugins),
        "plugins": plugins,
    }
