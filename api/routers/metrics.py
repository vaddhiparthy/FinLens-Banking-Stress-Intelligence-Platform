from fastapi import APIRouter

from api.services.repository import get_metrics

router = APIRouter()


@router.get("/metrics/{series_id}")
def metrics(series_id: str):
    return {"items": get_metrics(series_id)}
