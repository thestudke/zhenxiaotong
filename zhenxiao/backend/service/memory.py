import json
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession
from langchain_core.messages import HumanMessage, AIMessage

from model import Session as SessionModel, Message


def upsert_session(db: DBSession, 
                   session_id: str | None, 
                   first_message: str) -> str:
    if session_id:
        return session_id
    session_id = uuid.uuid4().hex
    db.add(SessionModel(id=session_id, title=first_message[:30]))
    db.commit()
    return session_id


def save_message(db: DBSession, 
                 session_id: str, 
                 role: str, 
                 content: str,
                 metadata: dict | None = None) -> None:
    db.add(Message(
        session_id=session_id,
        role=role,
        content=content,
        metadata_=json.dumps(metadata, ensure_ascii=False) if metadata else None,
    ))
    db.commit()


def load_history(db: DBSession, session_id: str, limit: int = 12) -> list:
    """读取最近 limit 条历史，转成 LangChain Message（时间正序）。"""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(desc(Message.id))
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    return [
        HumanMessage(content=r.content) if r.role == "user" else AIMessage(content=r.content)
        for r in rows
    ]
