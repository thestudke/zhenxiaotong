from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service.chat_service import run_chat
from route.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: DBSession = Depends(get_db)):
    """核心对话入口：接请求 → 调 Service → 返回结果。"""
    try:
        data = run_chat(
            db,
            session_id=req.session_id,
            user_id=req.user_id,
            message=req.message,
            patient_context=req.patient_context,
            enable_deep_search=req.enable_deep_search,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"agent 执行失败: {type(e).__name__}")
    return ChatResponse(**data)
