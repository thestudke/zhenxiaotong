from utils.state import AgentState
from utils import rules
from utils.compliance import compliance_guard, DISCLAIMER


def safety_agent(state: AgentState) -> dict:
    """SafetyAgent：合规检查 + 科室收敛 + 追加免责声明，组装最终 ChatResponse。"""
    structured = state["structured"] or {}
    scene = state["scene"]
    answer = compliance_guard(structured.get("answer", ""))

    # 规格书 3.1：推荐科室必须从系统科室列表中选取；3.3：用药咨询归一化为药学门诊
    # 收敛优先级：模型科室（含「呼吸内科」这类后缀偏差）> 答案文本中的科室 > 规则推测
    fallback_dept = rules.match_department(answer) or rules.suggest_department(answer or "", scene)
    recommended_department = rules.normalize_department(
        structured.get("recommended_department"), fallback_dept
    )

    # 规格书 6.3：证据返回最多 8 条
    evidence = (state.get("evidence") or [])[:rules.MAX_EVIDENCE]

    # 规格书 3.1：metrics 为本次推理的量化指标，模型未给时由链路补齐
    metrics = dict(structured.get("metrics") or {})
    metrics.setdefault("evidence_count", len(evidence))
    metrics.setdefault("retries", state.get("retries", 0))
    metrics.setdefault("mode", "llm")

    response = {
        "recommended_department": recommended_department,
        "risk_level": structured.get("risk_level"),
        "answer": answer,
        "evidence": evidence,
        "metrics": metrics,
        "disclaimer": DISCLAIMER,
        # 规格书 3.1：红旗信号 / 建议追问 / 健康建议随结构化结果一并返回
        "red_flags": structured.get("red_flags") or [],
        "follow_up_questions": structured.get("follow_up_questions") or [],
        "health_advice": structured.get("health_advice") or [],
    }
    return {
        "response": response,
        "thinking_steps": structured.get("thinking_steps") or [],
        "trace": [{"agent": "SafetyAgent", "action": "guard",
                   "detail": recommended_department or "", "duration_ms": 0}],
    }
