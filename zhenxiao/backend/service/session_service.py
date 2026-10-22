"""会话与数据管理：会话列表、消息读取、单会话删除与一键清空全部数据。

对应规格书 4.2 的 /api/sessions 系列端点与 3.7 的“一键清空全部数据”。
"""
from sqlalchemy import desc, func
from sqlalchemy.orm import Session as DBSession

from model import Session as SessionModel, Message, Encounter, Appointment
from utils import rules


def _session_out(db: DBSession, s: SessionModel) -> dict:
    msg_count = (
        db.query(func.count(Message.id))
        .filter(Message.session_id == s.id)
        .scalar()
        or 0
    )
    last = (
        db.query(Message.content)
        .filter(Message.session_id == s.id)
        .order_by(desc(Message.id))
        .first()
    )
    return {
        "id": s.id,
        "title": s.title or "",
        "message_count": msg_count,
        "last_message": (last[0] or "")[:60] if last else "",
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def list_sessions(db: DBSession, user_id: str | None = None) -> list:
    """会话列表，按更新时间倒序。"""
    rows = db.query(SessionModel).order_by(
        desc(SessionModel.updated_at), desc(SessionModel.created_at)
    ).all()
    return [_session_out(db, s) for s in rows]


def list_messages(
    db: DBSession,
    session_id: str,
    limit: int = rules.HISTORY_API_LIMIT,
) -> list | None:
    """会话消息（规格书 4.2：最多 100 条），按时间正序。返回 None 表示会话不存在。"""
    if not db.get(SessionModel, session_id):
        return None
    limit = max(1, min(int(limit or rules.HISTORY_API_LIMIT), rules.HISTORY_API_LIMIT))
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(desc(Message.id))
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


def delete_session(db: DBSession, session_id: str) -> bool:
    """删除指定会话及其消息、就诊记录。返回是否命中。"""
    s = db.get(SessionModel, session_id)
    if not s:
        return False
    db.query(Message).filter(Message.session_id == session_id).delete(
        synchronize_session=False
    )
    db.query(Encounter).filter(Encounter.session_id == session_id).delete(
        synchronize_session=False
    )
    db.delete(s)
    db.commit()
    return True


def clear_all(db: DBSession) -> dict:
    """规格书 3.7：清空 sessions、messages、encounters、appointments 四张表。"""
    counts = {
        "sessions": db.query(SessionModel).delete(synchronize_session=False),
        "messages": db.query(Message).delete(synchronize_session=False),
        "encounters": db.query(Encounter).delete(synchronize_session=False),
        "appointments": db.query(Appointment).delete(synchronize_session=False),
    }
    db.commit()
    return {"ok": True, "deleted": counts}
