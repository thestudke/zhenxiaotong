"""规格书 4.2：平台指标（会话/记录/预约/知识库规模与链路量化指标）。"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from model import get_db, Session as SessionModel, Message, Encounter, Appointment
from config import settings
from utils import llm, rules
from utils.rag_retriever import get_kb
from utils.report_fallback import REPORTS

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

TRACE_AGENTS = [
    "RouterAgent", "ContextAgent", "RAGAgent", "ResearchAgent",
    "ReasoningAgent", "FormatterAgent", "SafetyAgent", "FallbackAgent",
]


def _count(db: DBSession, model) -> int:
    return db.query(func.count(model.id)).scalar() or 0


@router.get("")
def _metrics(db: DBSession = Depends(get_db)):
    scene_rows = db.query(Encounter.scene, func.count(Encounter.id)).group_by(
        Encounter.scene
    ).all()
    appointment_rows = db.query(Appointment.status, func.count(Appointment.id)).group_by(
        Appointment.status
    ).all()

    return {
        "sessions": _count(db, SessionModel),
        "messages": _count(db, Message),
        "encounters": _count(db, Encounter),
        "encounters_by_scene": {s or "unknown": c for s, c in scene_rows},
        "appointments": _count(db, Appointment),
        "appointments_by_status": {s or "unknown": c for s, c in appointment_rows},
        "reports": len(REPORTS),
        "knowledge_chunks": len(get_kb().chunks),
        "departments": len(rules.DEPARTMENTS),
        "agents": TRACE_AGENTS,
        "llm_enabled": llm.is_enabled(),
        "rag_top_k": settings.rag_top_k,
        "max_evidence": rules.MAX_EVIDENCE,
        "history_limit": rules.HISTORY_LIMIT,
    }
