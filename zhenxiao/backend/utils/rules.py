"""本地规则：症状关键词 → 科室 / 风险等级，用于 ContextAgent 线索与规则兜底。"""

# 规格书附录 A：核心科室列表（唯一的科室事实来源，供前端下拉与 SafetyAgent 校验）
DEPARTMENTS = [
    "消化科", "妇产科", "皮肤科", "内分泌科", "神经内科", "骨科", "外科", "内科",
    "男科", "生殖医学科", "眼科", "肾脏病中心", "泌尿外科", "呼吸科", "药学门诊",
]

# 规格书 3.3：用药咨询场景固定归一化科室
MEDICATION_DEPARTMENT = "药学门诊"

# 规格书 6.3 数据规模约束
MAX_EVIDENCE = 8            # 证据返回上限
HISTORY_LIMIT = 12          # 上下文记忆上限
HISTORY_API_LIMIT = 100     # 会话消息接口上限
DEFAULT_RECORD_DAYS = 7     # 问诊记录默认天数

RED_FLAG_KEYWORDS = [
    "胸痛", "胸疼", "呼吸困难", "喘不上气", "憋气", "咯血", "吐血", "呕血", "便血",
    "意识", "昏迷", "抽搐", "晕厥", "窒息", "紫绀", "高热", "高烧", "持续呕吐", "急性", "剧烈",
]

# 规则表按规格书附录 A 的科室顺序排列（先匹配到的胜出，顺序本身即优先级）
DEPARTMENT_RULES = [
    (["腹痛", "肚子疼", "肚子痛", "腹泻", "拉肚子", "闹肚子", "呕吐", "恶心", "反胃", "想吐",
      "便秘", "胃痛", "胃胀", "腹胀", "胃", "消化", "食欲", "便血"], "消化科"),
    (["月经", "痛经", "白带", "妇科", "怀孕", "备孕", "孕期"], "妇产科"),
    (["皮疹", "起疹", "红疹", "疹", "瘙痒", "湿疹", "脱发", "痤疮", "长痘", "荨麻疹", "皮肤", "过敏"], "皮肤科"),
    (["多饮", "多尿", "血糖", "糖尿病", "消瘦", "甲状腺", "甲亢", "甲减"], "内分泌科"),
    (["头痛", "头疼", "头昏", "头晕", "眩晕", "抽搐", "麻木", "瘫痪", "记忆力",
      "失眠", "睡不着", "入睡困难", "睡眠障碍", "焦虑", "抑郁", "情绪低落"], "神经内科"),
    (["腰痛", "腰疼", "关节", "骨折", "扭伤", "颈椎", "肩", "膝盖", "腿疼", "胳膊疼", "后背疼", "骨"], "骨科"),
    (["外伤", "伤口", "肿块", "疝", "阑尾", "痔", "外科"], "外科"),
    (["血压", "高血压", "低血压", "心悸", "心慌", "胸闷", "内科"], "内科"),
    (["阳痿", "早泄", "包皮", "男科"], "男科"),
    (["不育", "生殖", "试管婴儿", "备孕检查"], "生殖医学科"),
    (["视力", "眼", "流泪", "干眼", "红肿"], "眼科"),
    (["尿频", "尿痛", "血尿", "尿血", "水肿", "肾", "蛋白尿", "尿蛋白"], "肾脏病中心"),
    (["尿急", "排尿", "前列腺", "泌尿"], "泌尿外科"),
    (["发热", "发烧", "咳嗽", "咳痰", "咽痛", "嗓子疼", "喉咙痛", "咽喉痛", "嗓子", "喉咙",
      "咽喉", "咽炎", "流涕", "鼻塞", "打喷嚏", "感冒", "呼吸困难", "喘不上气", "憋气",
      "气短", "胸痛", "胸疼"], "呼吸科"),
    (["药", "药物", "相互作用", "禁忌", "剂量", "布洛芬", "感冒灵"], "药学门诊"),
]


MEDICATION_KEYWORDS = [
    "用药", "服药", "吃药", "药物", "相互作用", "禁忌", "剂量", "副作用",
    "不良反应", "说明书", "处方", "布洛芬", "感冒灵", "抗生素", "消炎药",
    "退烧药", "止咳药", "止痛药", "怎么吃", "吃几", "吃多少", "能不能吃",
    "能一起吃", "一起吃", "什么药",
]


def suggest_scene(text: str) -> str:
    """规则路由：medication > triage（有症状线索） > consultation（默认）。"""
    t = expand(text)
    if any(k in t for k in MEDICATION_KEYWORDS):
        return "medication"
    if extract_clues(t):
        return "triage"
    return "consultation"


def suggest_department(text: str, scene: str | None = None) -> str:
    """症状 → 科室。用药咨询场景固定归一化为药学门诊（规格书 3.3）。"""
    if scene == "medication":
        return MEDICATION_DEPARTMENT
    expanded = expand(text)
    for kws, dept in DEPARTMENT_RULES:
        if any(k in expanded for k in kws):
            return dept
    return "内科"


# 口语 → 知识库/规则用词。仅用于本地规则的确定性匹配，不改变大模型输入原文。
SYNONYMS = {
    "孩子": "儿童", "小孩": "儿童", "宝宝": "儿童", "婴儿": "儿童",
    "发烧": "发热", "喘不上气": "呼吸困难", "喘不过气": "呼吸困难", "憋气": "呼吸困难",
    "胸口疼": "胸痛", "胸口痛": "胸痛", "拉肚子": "腹泻", "肚子疼": "腹痛",
    "睡不着": "失眠", "心慌": "心悸", "血压高": "高血压", "血糖高": "血糖",
}


def expand(text: str) -> str:
    """把口语说法展开为规范用词，供本地规则匹配使用。"""
    out = text or ""
    for colloquial, formal in SYNONYMS.items():
        if colloquial in out and formal not in out:
            out += " " + formal
    return out


def red_flags(text: str) -> list:
    expanded = expand(text)
    return [k for k in RED_FLAG_KEYWORDS if k in expanded]


def assess_risk(text: str) -> str:
    return "high" if red_flags(text) else "low"


def extract_clues(text: str) -> list:
    clues = list(red_flags(text))
    expanded = expand(text)
    for kws, dept in DEPARTMENT_RULES:
        if any(k in expanded for k in kws):
            clues.append(dept)
    return clues


def in_department_list(dept: str | None) -> bool:
    """规格书 3.1：推荐科室必须从系统科室列表中选取。"""
    return bool(dept) and dept in DEPARTMENTS


def match_department(dept: str | None) -> str | None:
    """把模型给的科室收敛到系统科室清单内。

    模型常见偏差是加后缀（「呼吸内科」→「呼吸科」），因此先精确匹配，
    再按"列表内科室名出现在模型输出中"的包含匹配兜底；仍匹配不上则返回 None。
    """
    if not dept:
        return None
    if dept in DEPARTMENTS:
        return dept
    matches = [d for d in DEPARTMENTS if d in dept]
    if matches:
        # 取最长匹配，避免「内科」抢占「呼吸内科」这类更具体的科室
        return max(matches, key=len)
    return None


def normalize_department(dept: str | None, fallback: str = "内科") -> str:
    """把模型给的科室收敛到系统科室清单内，收敛不了则用规则/默认科室。"""
    matched = match_department(dept)
    if matched:
        return matched
    return fallback if in_department_list(fallback) else DEPARTMENTS[-1]
