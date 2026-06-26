"""Guest router — GET /api/experts"""

import json
from pathlib import Path
from fastapi import APIRouter
from app.schemas.common import ApiResponse
from app.schemas.guest import GuestResponse

router = APIRouter()

# Load guests from JSON file
_guests_path = Path(__file__).parent.parent / "data" / "guests.json"
with open(_guests_path, "r", encoding="utf-8") as f:
    GUESTS: list[dict] = json.load(f)


@router.get("/experts", response_model=ApiResponse[list[GuestResponse]])
async def list_guests():
    """Return all 6 preset AI guests."""
    guests = [GuestResponse(**g) for g in GUESTS]
    return ApiResponse(data=guests)
