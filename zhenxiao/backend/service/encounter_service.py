"""问诊记录查询：规格书 3.5 FR-RECORD（近 7/30/180 天，可按场景过滤）。"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from model import Encounter
from utils import rules


def _out(e: Encounter) -> dict:
    return {
        "id": e.id,
        "session_id": e.session_id,
        "user_id": e.user_id,
        "scene": e.scene,
        "scene_label": {
            "triage": "智能分诊",
            "consultation": "线上问诊",
            "medication": "用药咨询",
        }.get(e.scene, e.scene or ""),
        "chief_complaint": e.chief_complaint,
        "risk_level": e.risk_level,
        "department": e.department,
        "summary": e.summary,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def list_encounters(
    db: DBSession,
    session_id: str | None = None,
    user_id: str | None = None,
    days: int | None = None,
    scene: str | None = None,
) -> list:
    """按创建时间倒序返回记录。days 为 1~365，None 表示不限（供 /api/encounters 兼容旧前端）。"""
    q = db.query(Encounter)
    if session_id:
        q = q.filter(Encounter.session_id == session_id)
    if user_id:
        q = q.filter(Encounter.user_id == user_id)
    if scene:
        q = q.filter(Encounter.scene == scene)
    if days:
        days = max(1, min(int(days), 365))
        since = datetime.now() - timedelta(days=days)
        q = q.filter(Encounter.created_at >= since)
    return [_out(e) for e in q.order_by(Encounter.created_at.desc()).all()]


def normalize_days(days: int | None) -> int:
    """规格书 3.5：days 1~365，默认 7。"""
    if days is None:
        return rules.DEFAULT_RECORD_DAYS
    return max(1, min(int(days), 365))
