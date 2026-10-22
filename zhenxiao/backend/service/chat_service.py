import json

from sqlalchemy.orm import Session as DBSession
from langchain_core.messages import HumanMessage

from model import Encounter
from service import memory
from agent.graph import graph
from utils import rules
from utils.state import initial_state


def _persist_encounter(
    db: DBSession,
    *,
    sid: str,
    user_id: str | None,
    scene: str,
    message: str,
    resp: dict,
) -> None:
    """规格书 3.1/3.2/3.3：分诊、问诊、用药三类场景均落库一条记录。"""
    db.add(Encounter(
        session_id=sid,
        user_id=user_id,
        scene=scene,
        chief_complaint=message,
        risk_level=resp.get("risk_level"),
        department=resp.get("recommended_department"),
        summary=resp.get("answer"),
        metadata_=json.dumps(resp, ensure_ascii=False),
    ))
    db.commit()


def run_chat(
    db: DBSession,
    *,
    session_id: str | None,
    user_id: str | None,
    message: str,
    patient_context: dict | None,
    enable_deep_search: bool,
    force_scene: str | None = None,
) -> dict:
    """核心对话编排：读历史 → 组装 state → 跑 graph → 落库 → 返回结构化结果。

    force_scene 供 /api/triage、/api/consultation、/api/medication 三个入口显式指定场景，
    为空时由 RouterAgent 规则判定。
    """
    sid = memory.upsert_session(db, session_id, message)
    history = memory.load_history(db, sid, limit=rules.HISTORY_LIMIT)
    messages = history + [HumanMessage(content=message)]

    state = initial_state(
        messages=messages,
        session_id=sid,
        patient_context=patient_context,
        enable_deep_search=enable_deep_search,
        forced_scene=force_scene,
    )

    result = graph.invoke(state)

    resp = result.get("response") or {}
    answer = resp.get("answer", "")
    scene = result.get("scene", "")

    metrics = dict(resp.get("metrics") or {})
    metrics.setdefault("mode", "fallback")

    # 规格书 6.3：证据返回最多 8 条
    evidence = (resp.get("evidence") or [])[:rules.MAX_EVIDENCE]

    response_payload = {
        "recommended_department": resp.get("recommended_department"),
        "risk_level": resp.get("risk_level"),
        "answer": answer,
        "evidence": evidence,
        "disclaimer": resp.get("disclaimer", ""),
        "metrics": metrics,
        "trace": result.get("trace") or [],
        "thinking_steps": result.get("thinking_steps") or [],
        "red_flags": resp.get("red_flags") or [],
        "follow_up_questions": resp.get("follow_up_questions") or [],
        "health_advice": resp.get("health_advice") or [],
    }

    memory.save_message(db, sid, "user", message)
    memory.save_message(db, sid, "assistant", answer, metadata=response_payload)

    # 三类场景统一落库，供“问诊记录”页按 7/30/180 天查询
    if scene in ("triage", "consultation", "medication"):
        _persist_encounter(
            db, sid=sid, user_id=user_id, scene=scene, message=message, resp=resp
        )

    return {"session_id": sid, "scene": scene, "answer": answer, **{
        k: v for k, v in response_payload.items() if k not in ("scene", "answer")
    }}
