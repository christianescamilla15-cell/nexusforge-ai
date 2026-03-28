from fastapi import APIRouter
from app.observability.metrics import collector

router = APIRouter()

@router.get('/metrics/summary')
async def get_metrics():
    return collector.get_summary()
