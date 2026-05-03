from fastapi import APIRouter, HTTPException

from api.services.repository import get_bank, list_failures

router = APIRouter()


@router.get("/failures")
def failures():
    return {"items": list_failures()}


@router.get("/banks/{bank_id}")
def bank(bank_id: str):
    row = get_bank(bank_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bank not found")
    return row
