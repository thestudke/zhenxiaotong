from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service.profile_service import get_profile, upsert_profile
from route.schemas import HealthProfileIn, HealthProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/{user_id}", response_model=HealthProfileOut)
def _get(user_id: str, db: DBSession = Depends(get_db)):
    data = get_profile(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="健康档案不存在")
    return HealthProfileOut(**data)


@router.put("/{user_id}", response_model=HealthProfileOut)
def _upsert(user_id: str, body: HealthProfileIn, db: DBSession = Depends(get_db)):
    return HealthProfileOut(**upsert_profile(db, user_id, body.model_dump()))
