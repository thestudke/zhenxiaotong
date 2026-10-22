from utils.state import AgentState, user_message
from utils import rules


def context_agent(state: AgentState) -> dict:
    """ContextAgent：整理患者信息与历史对话，产出本地症状线索（不得作为最终结论）。"""
    msg = user_message(state)
    local_clues = rules.extract_clues(msg) if msg else []
    if msg and rules.assess_risk(msg) == "high":
        local_clues.append("存在高危红旗信号")
    return {
        "local_clues": local_clues,
        "trace": [{"agent": "ContextAgent", "action": "context",
                   "detail": f"{len(local_clues)}条线索", "duration_ms": 0}],
    }
