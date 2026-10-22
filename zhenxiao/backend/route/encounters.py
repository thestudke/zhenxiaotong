from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service import encounter_service

router = APIRouter(prefix="/api/encounters", tags=["encounters"])


@router.get("")
def _list(
    session_id: str | None = None,
    user_id: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
    scene: str | None = None,
    db: DBSession = Depends(get_db),
):
    return encounter_service.list_encounters(
        db, session_id=session_id, user_id=user_id, days=days, scene=scene
    )
