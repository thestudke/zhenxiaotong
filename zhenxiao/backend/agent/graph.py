from langgraph.graph import StateGraph, START, END

from utils.state import AgentState
from agent.router import router_agent
from agent.context import context_agent
from agent.rag import rag_agent
from agent.research import research_agent
from agent.reasoning import reasoning_agent
from agent.formatter import formatter_agent
from agent.safety import safety_agent
from utils.fallback import fallback_agent

MAX_RETRIES = 3   # 规格书 3.8：重试 1~3 次，退避 0.8s 递增


def route_after_reasoning(state: AgentState) -> str:
    # LLM 未启用：规格书 2.4 要求直接降级，不走 Formatter 修复循环
    if state.get("llm_skipped"):
        return "fallback"
    if state["structured"] is not None:
        return "safety"
    return "formatter"


def route_after_formatter(state: AgentState) -> str:
    if state["structured"] is not None:
        return "safety"
    if state["retries"] >= MAX_RETRIES:
        return "fallback"
    return "reasoning"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("router", router_agent)
    builder.add_node("context", context_agent)
    builder.add_node("rag", rag_agent)
    builder.add_node("research", research_agent)
    builder.add_node("reasoning", reasoning_agent)
    builder.add_node("formatter", formatter_agent)
    builder.add_node("safety", safety_agent)
    builder.add_node("fallback", fallback_agent)

    # 主链
    builder.add_edge(START, "router")
    builder.add_edge("router", "context")

    # 并行 fan-out：context → rag / research（同一 superstep）
    builder.add_edge("context", "rag")
    builder.add_edge("context", "research")
    # join：两者都完成才进 reasoning
    builder.add_edge("rag", "reasoning")
    builder.add_edge("research", "reasoning")

    # 条件边：推理成功直接 safety，否则 formatter（条件触发）
    builder.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {"safety": "safety", "formatter": "formatter", "fallback": "fallback"},
    )
    
    builder.add_conditional_edges(
        "formatter",
        route_after_formatter,
        {
            "safety": "safety", 
            "reasoning": "reasoning",
            "fallback": "fallback"
            },
    )

    builder.add_edge("safety", END)
    builder.add_edge("fallback", END)

    return builder.compile()


graph = build_graph()
