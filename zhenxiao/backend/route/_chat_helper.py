"""三个场景化入口共用的调用逻辑，避免各路由重复组装参数。"""
from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from route.schemas import ChatRequest, ChatResponse
from service.chat_service import run_chat

SCENE_LABELS = {
    "triage": "智能分诊",
    "consultation": "线上问诊",
    "medication": "用药咨询",
}


def run_scene(db: DBSession, req: ChatRequest, scene: str) -> ChatResponse:
    """按指定场景执行多 Agent 链路（规格书 3.1 / 3.2 / 3.3）。"""
    try:
        data = run_chat(
            db,
            session_id=req.session_id,
            user_id=req.user_id,
            message=req.message,
            patient_context=req.patient_context,
            enable_deep_search=req.enable_deep_search,
            force_scene=scene,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{SCENE_LABELS.get(scene, scene)}执行失败: {type(e).__name__}",
        )
    return ChatResponse(**data)
