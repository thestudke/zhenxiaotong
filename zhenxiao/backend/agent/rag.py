import time

from config import settings
from utils.state import AgentState, user_message
from utils.rag_retriever import get_kb


def rag_agent(state: AgentState) -> dict:
    """RAGAgent：检索本地知识库，召回证据（规格书 3.9：分诊/问诊链路默认 6 条）。"""
    t0 = time.time()
    msg = user_message(state)
    query = msg
    if state["scene"] == "medication":
        query = f"{msg} 用药安全 药物相互作用 禁忌 特殊人群"
    evidence = [e.to_dict() for e in get_kb().search(query, top_k=settings.rag_top_k)]
    return {
        "evidence": evidence,
        "trace": [{"agent": "RAGAgent", "action": "retrieve",
                   "detail": f"{len(evidence)}条", "duration_ms": int((time.time() - t0) * 1000)}],
    }
