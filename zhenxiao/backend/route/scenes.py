"""规格书 3.1 / 3.2 / 3.3：智能分诊、线上问诊、用药咨询三个场景化入口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from model import get_db
from route.schemas import ChatRequest, ChatResponse
from route._chat_helper import run_scene

router = APIRouter(prefix="/api", tags=["scenes"])


@router.post("/triage", response_model=ChatResponse)
def triage(req: ChatRequest, db: DBSession = Depends(get_db)):
    """智能分诊：强制 triage 场景。"""
    return run_scene(db, req, "triage")


@router.post("/consultation", response_model=ChatResponse)
def consultation(req: ChatRequest, db: DBSession = Depends(get_db)):
    """线上问诊：强制 consultation 场景，带短期记忆。"""
    return run_scene(db, req, "consultation")


@router.post("/medication", response_model=ChatResponse)
def medication(req: ChatRequest, db: DBSession = Depends(get_db)):
    """用药咨询：强制 medication 场景，科室归一化为药学门诊。"""
    return run_scene(db, req, "medication")
