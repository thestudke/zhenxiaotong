from typing import List

from utils.state import AgentState, user_message
from utils import rules
from utils.compliance import compliance_guard, DISCLAIMER
from utils.rag_retriever import _char_ngrams

# 合规边界文档不参与降级回答的素材（避免把"不得确诊"这类元规则当医学建议输出）
_EXCLUDED_SOURCES = ("06_医疗合规与问诊边界.md",)

# 相关性分层：以最高分为基准的相对阈值（绝对余弦值受文本长度影响，不可直接当阈值用）
_HIGH_REL = 0.5      # 第一层：与最佳命中同量级，直接作为回答素材
_LOW_REL = 0.25      # 第二层：第一层不足 2 条时的补充（0.3 会漏掉口语化提问）
_FLAG_REL = 0.15     # 出现高危症状时放宽，保证急救类条目能作为素材
_TITLE_OVERLAP = 0.5  # 第二层补充块要求题名与提问的字面重合比例
_MIN_POINTS = 2

# 口语同义词由 utils.rules 统一维护，避免多处口径不一致（见 rules.expand）

MAX_POINTS = 3       # 最终展示的要点数
MAX_PER_SOURCE = 2   # 同一文档最多贡献的要点数，保证覆盖不同角度
POINT_CHARS = 110
MAX_ANSWER_CHARS = 420

_SCENE_TITLES = {
    "consultation": "结合本地知识库的解答",
    "medication": "结合本地知识库的用药安全参考",
    "triage": "结合本地知识库的初步分析",
}

# 人群标记：提问提到儿童/孕妇时，不应优先引用其他人群的条目（反之亦然）
_POPULATIONS = {
    "儿童": ("儿童", "孩子", "小孩", "宝宝", "婴儿", "婴幼儿"),
    "孕妇": ("孕妇", "孕期", "怀孕", "哺乳", "备孕"),
    "老年": ("老人", "老年", "爷爷", "奶奶"),
}


def _populations(text: str) -> set:
    return {name for name, words in _POPULATIONS.items() if any(w in (text or "") for w in words)}


def _split_sentences(text: str) -> List[str]:
    """把知识库段落拆成句子，保留信息量足够、合规的句子。"""
    out: List[str] = []
    for raw in (text or "").replace("\n", " ").split("。"):
        s = raw.strip(" -•·\t")
        if len(s) < 8:
            continue
        if "不能" in s and "替代" in s:
            continue
        if "不得" in s or ("避免" in s and "确诊" in s):
            continue
        out.append(s)
    return out


def _expand(text: str) -> str:
    """把口语说法展开为知识库用词，提升相关性判定命中率。"""
    return rules.expand(text)


def _title_matches(query: str, section_title: str, source: str = "") -> bool:
    """题名与提问是否"实质相关"。

    只共用一个二字词（如问"发热"命中"儿童发热"、问"能吃"命中"常见可能原因"）
    不足以判定相关，需要字面重合达到一定比例，避免把其他人群/其他主题的条目当素材。
    章节标题过短时，用「文档名 + 章节名」一起参与判定。
    """
    if not query:
        return False
    q_grams = set(_char_ngrams(_expand(query)))

    candidates = [section_title or ""]
    doc_title = (source or "").split("_", 1)[-1].rsplit(".md", 1)[0]
    if doc_title:
        candidates.append(doc_title)
        candidates.append(f"{doc_title}{section_title or ''}")

    for cand in candidates:
        t_grams = set(_char_ngrams(cand))
        if not t_grams:
            continue
        common = q_grams & t_grams
        if common and len(common) / len(t_grams) >= _TITLE_OVERLAP:
            return True
    return False


def _relevant(evidence: List[dict], query: str = "", scene: str = "") -> List[dict]:
    """筛出与问题真正相关的知识块。

    只用绝对分数会混入弱相关文档（如问血压却召回胃肠道文档），因此分两层：
    第一层按相对得分；第一层不足 2 条时，第二层补充的块还必须与提问实质相关。
    用药咨询场景放宽（阈值与题名共用词都少），高危症状场景放宽（需保住急救条目）。
    """
    items = [
        e for e in evidence
        if e.get("source") not in _EXCLUDED_SOURCES and e.get("content")
    ]
    if not items:
        return []
    items.sort(key=lambda e: -float(e.get("score") or 0))
    top = float(items[0].get("score") or 0)
    if top <= 0:
        return items

    # 人群匹配：提问与条目的人群标记必须一致。
    # 否则问成人发热会被"儿童发热"条目抢占，问儿童则可能被成人条目抢占。
    q_pop = _populations(query)
    matched = [
        e for e in items
        if _populations(f"{e.get('source') or ''}{e.get('title') or ''}") <= q_pop
    ]
    if matched:
        items = matched
        top = float(items[0].get("score") or 0)

    top_source = items[0].get("source")

    def relevant_block(e: dict) -> bool:
        """同一文档的块默认可信；跨文档的块必须题名与提问实质相关。"""
        if e.get("source") == top_source:
            return True
        return _title_matches(query, e.get("title") or "", e.get("source") or "")

    picked = [
        e for e in items
        if float(e.get("score") or 0) >= top * _HIGH_REL and relevant_block(e)
    ]
    if len(picked) >= _MIN_POINTS:
        return picked

    low_rel = _LOW_REL
    if scene == "medication":
        low_rel = _LOW_REL * 0.8
    if rules.red_flags(query):
        low_rel = min(low_rel, _FLAG_REL)

    # 补充素材只允许来自"最佳命中所在文档"，避免为凑要点跨主题拼凑
    for e in items:
        if e.get("source") != top_source or e in picked:
            continue
        if float(e.get("score") or 0) < top * low_rel:
            continue
        if not _title_matches(query, e.get("title") or "", e.get("source") or ""):
            continue
        picked.append(e)

    return picked


def select_points(evidence: List[dict], query: str = "", scene: str = "") -> List[str]:
    """挑出要点：优先覆盖不同文档，同一文档最多 2 条。"""
    picked: List[str] = []
    per_source: dict = {}

    for ev in _relevant(evidence, query, scene):
        title = (ev.get("title") or "").strip()
        source = ev.get("source") or ""
        if per_source.get(source, 0) >= MAX_PER_SOURCE:
            continue
        for sent in _split_sentences(ev.get("content", "")):
            point = f"{title}：{sent}。" if title else f"{sent}。"
            if point in picked:
                continue
            picked.append(point)
            per_source[source] = per_source.get(source, 0) + 1
            break
        if len(picked) >= MAX_POINTS:
            break
    return picked


def synthesize_answer(evidence: List[dict], scene: str, query: str = "") -> str:
    """降级模式下的轻量规则摘要：把 RAG 证据整理成"先回答用户问题"的科普内容。

    非医学结论：只做知识库原文的筛选、排序与摘录，不推断、不给出诊断或处方剂量。
    无可用证据时返回空串，由调用方退回纯规则模板。
    """
    points = select_points(evidence, query, scene)
    if not points:
        return ""
    lines = [f"{i + 1}. {p[:POINT_CHARS]}" for i, p in enumerate(points)]
    header = _SCENE_TITLES.get(scene, "参考信息")
    return f"{header}：\n" + "\n".join(lines)[:MAX_ANSWER_CHARS]


def _fallback_answer(msg: str, scene: str, dept: str, risk: str, evidence: List[dict]) -> tuple:
    """先回答用户问题，再给出就医/用药建议。返回 (答案, 素材来源)。"""
    parts: List[str] = []

    summary = synthesize_answer(evidence, scene, msg)
    if summary:
        parts.append(summary)
        source = "kb_summary"
    else:
        # 无本地证据时的通用提示（不臆造结论）
        source = "template"
        if scene == "medication":
            parts.append(
                "本地知识库暂无与您描述完全匹配的药学资料，无法就具体药物组合给出判断。"
            )
        else:
            parts.append(
                "本地知识库暂无与您描述完全匹配的条目，以下为通用就医参考，建议现场由医生结合检查判断。"
            )

    if scene == "medication":
        parts.append(
            f"就医与用药边界：用药安全建议咨询【{dept}】或药师；"
            "不同药物可能存在相互作用或成分重复，不建议自行叠加服用，"
            "具体是否用药、用多久需要医生或药师评估。"
        )
    elif risk == "high":
        parts.append(f"风险提示：您的描述中包含需要重视的高危信号，建议尽快前往【{dept}】线下就医或急诊。")
    else:
        parts.append(
            f"就医建议：如症状持续或加重，建议前往【{dept}】门诊评估；"
            "症状轻微时可先按上述内容自我观察，不建议自行用药。"
        )

    return compliance_guard("\n\n".join(parts)), source


def fallback_agent(state: AgentState) -> dict:
    """规则兜底：模型不可用/解析失败时，用「本地规则 + RAG 知识库摘要」给出回答。

    规格书 2.4：不强制依赖真实大模型；规格书 3.10：仅作参考并保留免责声明。
    """
    msg = user_message(state)
    scene = state.get("scene", "")
    # 规格书 3.3：用药咨询降级时同样必须归一化为药学门诊
    dept = rules.suggest_department(msg, scene)
    risk = rules.assess_risk(msg)
    evidence = (state.get("evidence") or [])[:rules.MAX_EVIDENCE]
    answer, source = _fallback_answer(msg, scene, dept, risk, evidence)

    response = {
        "recommended_department": dept,
        "risk_level": risk,
        "answer": answer,
        "evidence": evidence,
        "metrics": {
            "mode": "fallback",
            "evidence_count": len(evidence),
            "llm_enabled": False,
            "answer_source": source,
        },
        "disclaimer": DISCLAIMER,
        "red_flags": rules.red_flags(msg),
        "follow_up_questions": [],
        "health_advice": [],
    }
    return {
        "response": response,
        "thinking_steps": [
            "LLM 未启用或输出不可解析，已降级为本地规则 + RAG 知识库摘要兜底"
        ],
        "trace": [{"agent": "FallbackAgent", "action": "fallback",
                   "detail": f"{dept} / {risk} / {len(evidence)}条证据", "duration_ms": 0}],
    }
