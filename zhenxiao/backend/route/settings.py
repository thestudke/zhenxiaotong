"""规格书 3.7 / 4.2：系统设置状态（模型、API 地址、联网检索、rag_top_k）。"""
from fastapi import APIRouter

from agent.research import check_availability
from config import settings
from utils import llm, rules

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def _settings():
    """不展示 API Key 明文，仅返回是否已配置。"""
    search_issue = check_availability()
    return {
        "llm_enabled": llm.is_enabled(),
        "base_url": settings.dashscope_base_url or "",
        "model_name": settings.dashscope_chat_model or "",
        "api_key_configured": bool(settings.dashscope_api_key_2),
        "deep_search_enabled": bool(settings.deep_search_enabled),
        "deep_search_key_configured": bool(settings.tavily_api_key),
        # 联网检索的实际可用性：空串=可用，非空=不可用原因（便于排查）
        "deep_search_available": not search_issue,
        "deep_search_issue": search_issue,
        "rag_top_k": settings.rag_top_k,
        "departments": rules.DEPARTMENTS,
        "knowledge_base": "本地 Markdown（data/knowledge_base）",
        "database": settings.db_url.split("://", 1)[0],
        "version": "2.1.0",
    }
