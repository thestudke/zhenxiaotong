from typing import Annotated, Optional, List
import operator

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """诊小通 Agent 的图状态。
    service 层把 DB 里的历史 + 当前用户消息转成 LangChain Message 后塞进来，
    ContextAgent 直接读 messages[-12:] 作为上下文。
    """        
    # —— 入参 ——
    patient_context: Optional[dict]   
    session_id: Optional[str]
    enable_deep_search: bool
    forced_scene: Optional[str]        # 接口层强制场景（/api/triage 等），为空则由 RouterAgent 规则判定

    # —— 路由与上下文 ——
    scene: str                        # triage / consultation / medication
    local_clues: List[str]            # ContextAgent 本地症状线索

    # —— 证据：rag 与 research 并行写入，用 operator.add 合并而非覆盖 ——
    evidence: Annotated[List[dict], operator.add]

    # —— 推理 ——
    reasoning_raw: str                # LLM 原始输出
    structured: Optional[dict]        # 解析成功的 JSON 结果
    retries: int                      # 重试计数（覆盖式，非累积）
    llm_skipped: bool                 # LLM 未启用，直接走规则兜底

    # —— 输出与审计 ——
    response: dict                    # 最终 ChatResponse
    trace: Annotated[List[dict], operator.add]   # AgentTrace 累积，每个节点 append 一条
    thinking_steps: List[str]


def initial_state(**overrides) -> dict:
    """返回一份字段齐全的初始 state，避免 graph.invoke 时因缺 key 报错。"""
    base = {
        "messages": [],
        "patient_context": None,
        "session_id": None,
        "enable_deep_search": True,
        "forced_scene": None,
        "scene": "",
        "local_clues": [],
        "evidence": [],
        "reasoning_raw": "",
        "structured": None,
        "retries": 0,
        "llm_skipped": False,
        "response": {},
        "trace": [],
        "thinking_steps": [],
    }
    base.update(overrides)
    return base


def _content(m) -> str:
    if isinstance(m, dict):
        return m.get("content", "") or ""
    return getattr(m, "content", "") or ""


def user_message(state) -> str:
    """当前用户消息（messages 最后一条）。"""
    msgs = state.get("messages") or []
    return _content(msgs[-1]) if msgs else ""


def history_texts(state, limit: int = 12) -> List[str]:
    """历史对话文本（不含最后一条当前消息），时间正序。"""
    msgs = state.get("messages") or []
    return [_content(m) for m in msgs[:-1]][-limit:]
