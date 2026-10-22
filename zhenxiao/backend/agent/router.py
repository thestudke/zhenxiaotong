import time

from utils.state import AgentState, user_message
from utils import rules


def router_agent(state: AgentState) -> dict:
    """RouterAgent：识别业务场景（triage / consultation / medication）。

    规则路由（无 LLM，确定性、低延迟）：用药关键词 → medication；
    有症状/红旗线索 → triage；否则（寒暄/追问/无明确症状）→ consultation。
    接口层显式指定场景（/api/triage|consultation|medication）时以指定值为准。
    """
    t0 = time.time()
    msg = user_message(state)
    forced = state.get("forced_scene")
    if forced:
        scene = forced
        detail = f"{forced}(forced)"
    else:
        scene = rules.suggest_scene(msg) if msg else "consultation"
        detail = scene
    return {
        "scene": scene,
        "trace": [{"agent": "RouterAgent", "action": "route", "detail": detail,
                   "duration_ms": int((time.time() - t0) * 1000)}],
    }
