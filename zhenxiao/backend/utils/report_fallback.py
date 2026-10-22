"""报告解读的规则兜底：内置模拟报告数据 + 异常判定 + 规则解读。"""

REPORTS = [
    {
        "id": "report_cbc",
        "name": "血常规",
        "department": "血液科",
        "exam_date": "2026-09-20",
        "items": [
            {"name": "白细胞计数(WBC)", "value": "11.5", "unit": "×10^9/L", "reference_range": "3.5-9.5", "flag": "偏高"},
            {"name": "中性粒细胞百分比(NEUT%)", "value": "78", "unit": "%", "reference_range": "40-75", "flag": "偏高"},
            {"name": "红细胞计数(RBC)", "value": "4.5", "unit": "×10^12/L", "reference_range": "3.8-5.1", "flag": "正常"},
            {"name": "血红蛋白(HGB)", "value": "135", "unit": "g/L", "reference_range": "115-150", "flag": "正常"},
            {"name": "血小板计数(PLT)", "value": "210", "unit": "×10^9/L", "reference_range": "125-350", "flag": "正常"},
        ],
    },
    {
        "id": "report_ct",
        "name": "胸部 CT",
        "department": "呼吸科",
        "exam_date": "2026-09-18",
        "items": [
            {"name": "肺部结节", "value": "右肺上叶小结节影（约5mm）", "unit": "", "reference_range": "无结节", "flag": "异常"},
            {"name": "纵隔淋巴结", "value": "未见肿大", "unit": "", "reference_range": "未见肿大", "flag": "正常"},
            {"name": "胸腔积液", "value": "无", "unit": "", "reference_range": "无", "flag": "正常"},
            {"name": "胸膜", "value": "无增厚", "unit": "", "reference_range": "无增厚", "flag": "正常"},
        ],
    },
    {
        "id": "report_liver_kidney",
        "name": "肝肾功能",
        "department": "肾内科",
        "exam_date": "2026-09-15",
        "items": [
            {"name": "丙氨酸氨基转移酶(ALT)", "value": "68", "unit": "U/L", "reference_range": "7-40", "flag": "偏高"},
            {"name": "天门冬氨酸氨基转移酶(AST)", "value": "52", "unit": "U/L", "reference_range": "13-35", "flag": "偏高"},
            {"name": "肌酐(Cr)", "value": "88", "unit": "μmol/L", "reference_range": "44-133", "flag": "正常"},
            {"name": "尿素氮(BUN)", "value": "5.2", "unit": "mmol/L", "reference_range": "2.9-8.2", "flag": "正常"},
        ],
    },
]


def compute_risk(items: list) -> str:
    """异常项判定：items[].flag != "正常" 即异常；有异常为中风险，否则低风险。"""
    return "medium" if any(i.get("flag") != "正常" for i in items) else "low"


def analyze_items(items: list) -> str:
    abnormal = [i for i in items if i.get("flag") != "正常"]
    if not abnormal:
        return "各项指标均在参考范围内"
    return "异常指标：" + "、".join(f"{i['name']}({i['flag']})" for i in abnormal)


def find_report(report_id: str) -> dict | None:
    for r in REPORTS:
        if r["id"] == report_id:
            return r
    return None


def report_fallback(report: dict) -> str:
    """规则兜底解读：基于异常项生成就医建议，无模型时使用。"""
    items = report["items"]
    abnormal = [i for i in items if i.get("flag") != "正常"]
    dept = report["department"]
    if not abnormal:
        return (
            f"本次【{report['name']}】各项指标均在参考范围内，暂无需特殊处理。"
            "建议保持健康生活方式，并按医嘱定期复查。"
        )
    lines = [f"本次【{report['name']}】提示以下异常："]
    for i in abnormal:
        lines.append(f"- {i['name']}：{i['value']}（参考范围 {i['reference_range']}），结果{i['flag']}")
    lines.append(f"以上指标异常需结合临床症状综合判断，建议携带本报告前往【{dept}】门诊进一步就诊。")
    return "\n".join(lines)
