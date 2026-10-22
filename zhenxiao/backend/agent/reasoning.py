import time

from utils.state import AgentState
from utils import llm, prompts
from utils.json_tools import try_parse_json


def reasoning_agent(state: AgentState) -> dict:
    """ReasoningAgent：大模型结构化推理，首次尝试 JSON 解析。"""
    if not llm.is_enabled():
        # 规格书 2.4：不强制依赖真实大模型。未启用时直接标记 skip，
        # 由 graph 条件边直达 FallbackAgent，避免 Reasoning↔Formatter 空转。
        return {
            "reasoning_raw": "", "structured": None, "llm_skipped": True,
            "trace": [{"agent": "ReasoningAgent", "action": "reason",
                       "detail": "llm disabled, skip", "duration_ms": 0}],
        }
    if state["retries"] > 0:
        time.sleep(0.8 * state["retries"])   # 退避 0.8s 递增

    system = prompts.system_prompt(state["scene"])
    user = prompts.build_user_prompt(state)
    t0 = time.time()
    try:
        raw = llm.chat(system, user)
    except Exception as e:
        return {
            "reasoning_raw": "", "structured": None,
            "trace": [{"agent": "ReasoningAgent", "action": "reason",
                       "detail": f"error: {type(e).__name__}", "duration_ms": 0}],
        }
    duration_ms = int((time.time() - t0) * 1000)
    structured = try_parse_json(raw)
    return {
        "reasoning_raw": raw,
        "structured": structured,
        "trace": [{"agent": "ReasoningAgent", "action": "reason",
                   "detail": f"parsed={structured is not None}", "duration_ms": duration_ms}],
    }
