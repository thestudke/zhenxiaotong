"""规格书 4.2：会话列表、会话消息、删除会话、清空全部数据。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service import session_service
from utils import rules

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def _list(user_id: str | None = None, db: DBSession = Depends(get_db)):
    return {"sessions": session_service.list_sessions(db, user_id)}


@router.get("/{session_id}/messages")
def _messages(
    session_id: str,
    limit: int = Query(rules.HISTORY_API_LIMIT, ge=1, le=rules.HISTORY_API_LIMIT),
    db: DBSession = Depends(get_db),
):
    rows = session_service.list_messages(db, session_id, limit)
    if rows is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "count": len(rows), "messages": rows}


@router.delete("/{session_id}")
def _delete(session_id: str, db: DBSession = Depends(get_db)):
    if not session_service.delete_session(db, session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True, "session_id": session_id}


@router.delete("")
def _clear(db: DBSession = Depends(get_db)):
    """规格书 3.7：一键清空 sessions / messages / encounters / appointments 四张表。"""
    return session_service.clear_all(db)
