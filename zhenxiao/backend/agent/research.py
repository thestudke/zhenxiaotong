import time

from config import settings
from utils.state import AgentState, user_message

DEGRADED_TITLE = "联网检索暂不可用"
DEGRADED_CONTENT = "本次未能获取联网资料，将基于本地知识库与安全规则回答，仅供参考。"


def _degraded_evidence(reason: str) -> dict:
    """规格书 3.10：检索失败/未开启时返回一条降级证据，提示将基于本地知识库回答。"""
    return {
        "source": "deep_search_fallback",
        "title": DEGRADED_TITLE,
        "score": 0.0,
        "content": f"{DEGRADED_CONTENT}（原因：{reason}）",
    }


def check_availability() -> str:
    """预检联网检索是否可用，返回空串表示可用，否则返回不可用原因。

    单独抽出来是为了让"未装 tavily 包"这类问题在服务启动时就能暴露，
    而不是等到用户提问时才在界面上显示一句"暂不可用"。
    """
    if not settings.deep_search_enabled:
        return "已在配置中关闭（DEEP_SEARCH_ENABLED=false）"
    if not settings.tavily_api_key:
        return "未配置 TAVILY_API_KEY"
    try:
        import tavily  # noqa: F401
    except ImportError as e:
        return (
            f"缺少 Python 依赖 tavily-python（{e}），"
            "请在当前解释器中执行：pip install tavily-python"
        )
    return ""


def research_agent(state: AgentState) -> dict:
    """ResearchAgent：联网 DeepResearch（规格书 3.10）。

    与 RAGAgent 并行，证据通过 evidence 合并；联网资料仅作参考。
    未开启 / 未配置 key / 检索异常时返回一条降级证据，不影响主链路。
    """
    if not state["enable_deep_search"]:
        return {
            "trace": [{"agent": "ResearchAgent", "action": "deep_search",
                       "detail": "disabled by request", "duration_ms": 0}],
        }

    msg = user_message(state)
    t0 = time.time()
    evidence: list[dict] = []

    unavailable = check_availability()
    if unavailable:
        detail = unavailable
    elif not msg:
        detail = "提问为空，未发起检索"
    else:
        detail = "检索未返回结果"
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            resp = client.search(query=msg, search_depth="basic", max_results=3)
            for r in resp.get("results", []):
                content = (r.get("content") or "").strip()
                if not content:
                    continue
                evidence.append({
                    "source": r.get("url", ""),
                    "title": r.get("title", ""),
                    "score": float(r.get("score", 0.0)),
                    "content": content[:500],
                })
            if evidence:
                detail = f"{len(evidence)}条"
        except Exception as e:
            # 带上异常信息，便于定位（如网络不可达、key 无效、配额用尽）
            detail = f"检索失败：{type(e).__name__}: {e}"

    if not evidence:
        evidence = [_degraded_evidence(detail)]

    return {
        "evidence": evidence,
        "trace": [{"agent": "ResearchAgent", "action": "deep_search",
                   "detail": detail, "duration_ms": int((time.time() - t0) * 1000)}],
    }
