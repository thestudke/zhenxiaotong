from utils.state import AgentState
from utils.json_tools import repair_json


def formatter_agent(state: AgentState) -> dict:
    """FormatterAgent：输出非法 JSON 时修复（条件触发）。"""
    repaired = repair_json(state["reasoning_raw"])
    if repaired:
        return {
            "structured": repaired,
            "trace": [{"agent": "FormatterAgent", "action": "repair",
                       "detail": "repaired", "duration_ms": 0}],
        }
    return {
        "retries": state["retries"] + 1,
        "trace": [{"agent": "FormatterAgent", "action": "repair",
                   "detail": "failed", "duration_ms": 0}],
    }
