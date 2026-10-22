from utils import llm, prompts
from utils.compliance import compliance_guard
from utils.report_fallback import (
    REPORTS,
    compute_risk,
    analyze_items,
    find_report,
    report_fallback,
)


def list_reports() -> list:
    """返回每个用户内置的 3 份模拟报告（含指标明细与预计算风险）。"""
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "department": r["department"],
            "exam_date": r["exam_date"],
            "items": r["items"],
            "risk_level": compute_risk(r["items"]),
        }
        for r in REPORTS
    ]


def interpret_report(report_id: str) -> dict | None:
    r = find_report(report_id)
    if not r:
        return None
    analysis = analyze_items(r["items"])
    return {
        "id": r["id"],
        "department": r["department"],
        "risk_level": compute_risk(r["items"]),
        "analysis": analysis,
        "interpretation": _interpret(r, analysis),
    }


def _interpret(report: dict, analysis: str) -> str:
    if llm.is_enabled():
        try:
            raw = llm.chat(
                prompts.REPORT_SYSTEM_PROMPT,
                prompts.build_report_user_prompt(report, analysis),
            )
            return compliance_guard(raw)
        except Exception:
            pass
    return compliance_guard(report_fallback(report))
