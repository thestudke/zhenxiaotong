"""规格书 3.5 / 4.2：问诊记录查询（近 7/30/180 天）。

同时提供 /api/records（规格书清单）与 /api/encounters（既有前端约定）两个入口。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service import encounter_service
from utils import rules

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/records")
def _records(
    user_id: str | None = None,
    days: int = Query(rules.DEFAULT_RECORD_DAYS, ge=1, le=365),
    scene: str | None = None,
    db: DBSession = Depends(get_db),
):
    """规格书 3.5：输出 {records:[...]}，days 取 1~365，默认 7。"""
    normalized = encounter_service.normalize_days(days)
    rows = encounter_service.list_encounters(
        db, user_id=user_id, days=normalized, scene=scene
    )
    return {
        "records": rows,
        "total": len(rows),
        "days": normalized,
        "user_id": user_id,
    }
