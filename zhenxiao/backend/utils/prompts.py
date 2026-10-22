from utils import rules
from utils.state import user_message, history_texts

_JSON_TRIAGE = (
    '{"recommended_department":"科室名","risk_level":"low|medium|high",'
    '"answer":"对外可读的精炼答案","evidence":["依据1"],'
    '"red_flags":["红旗信号"],"follow_up_questions":["追问"],"health_advice":["健康建议"]}'
)

# 规格书 3.1：推荐科室必须从系统科室列表（附录 A）中选取
_DEPT_RULE = (
    "recommended_department 必须从以下系统科室列表中逐字选取一个，不得自造科室名"
    "（禁止出现「呼吸内科」「心血管内科」等列表外的名称）："
    + "、".join(rules.DEPARTMENTS)
    + "。"
)

SYSTEM_PROMPTS = {
    "triage": (
        "你是互联网医院的智能分诊助手。根据患者症状与病史给出推荐挂号科室、风险等级与分诊建议。"
        "不得确诊、不得开处方、不得给出具体剂量。"
        + _DEPT_RULE
        + "严格按 JSON 输出（不要输出 JSON 以外内容）：\n"
        + _JSON_TRIAGE
    ),
    "consultation": (
        "你是互联网医院的线上问诊助手，进行聊天式连续问诊，可结合上下文追问。"
        "不得确诊、不得开处方。"
        + _DEPT_RULE
        + "严格按 JSON 输出：\n"
        '{"answer":"回答","risk_level":"low|medium|high",'
        '"recommended_department":"建议科室","follow_up_questions":["追问"]}'
    ),
    "medication": (
        "你是药学咨询助手，围绕药物相互作用、重复用药、禁忌与慎用人群、特殊人群（孕妇/儿童/老年人/肝肾功能不全）"
        "与就医边界提供参考。不得给出具体处方剂量。recommended_department 固定为「药学门诊」。"
        "严格按 JSON 输出（不要输出 JSON 以外内容）：\n"
        '{"recommended_department":"药学门诊","answer":"用药安全参考","risk_level":"low|medium|high",'
        '"red_flags":["危险信号"],"follow_up_questions":["追问"],"health_advice":["建议"]}'
    ),
}


def system_prompt(scene: str) -> str:
    return SYSTEM_PROMPTS.get(scene, SYSTEM_PROMPTS["triage"])


def build_user_prompt(state) -> str:
    parts = []
    msg = user_message(state)
    if msg:
        parts.append(f"用户主诉：{msg}")
    pc = state.get("patient_context")
    if pc:
        parts.append(f"患者信息：{pc}")
    hist = history_texts(state, limit=4)
    if hist:
        parts.append("历史对话：" + "；".join(hist))
    clues = state.get("local_clues") or []
    if clues:
        parts.append("本地症状线索：" + "、".join(clues))
    evidence = state.get("evidence") or []
    if evidence:
        evs = [f"[{e.get('title')}] {e.get('content', '')[:120]}" for e in evidence[:6]]
        parts.append("参考证据：\n" + "\n".join(evs))
    return "\n\n".join(parts)


REPORT_SYSTEM_PROMPT = (
    "你是互联网医院的检查报告解读助手。仅提供通俗的科普解释与就医建议，"
    "不得确诊、不得开处方、不得给出具体治疗药物或剂量。"
)


def build_report_user_prompt(report: dict, analysis: str) -> str:
    lines = [f"报告名称：{report['name']}", f"所属科室：{report['department']}"]
    lines.append("指标明细：")
    for i in report["items"]:
        lines.append(f"- {i['name']}：{i['value']}（参考 {i['reference_range']}），{i['flag']}")
    lines.append(f"异常分析：{analysis}")
    lines.append("请分点给出：1) 异常指标的通俗科普解释；2) 就医建议。")
    return "\n".join(lines)

