"""Autonomous AI Roundtable — experts self-decide when to speak.

Flow:
  INIT → HOST_INTRO → AUTONOMOUS_DISCUSSION → HOST_SUMMARY → END

Key differences from v2:
- Experts independently decide when to "raise hand" (no moderator dictate)
- Each speech: 1-2 sentences only
- Expert status tracked: idle → preparing → speaking → idle
- Concurrent LLM calls for expert decisions (asyncio.gather)
"""

import json
import asyncio
import operator
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.types import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.services.llm_service import get_llm_service, LLMService
from app.services.prompt_manager import (
    HOST_SYSTEM_PROMPT,
    build_expert_system_prompt,
    build_opening_prompt,
    build_expert_decide_prompt,
    build_host_followup_prompt,
    build_expert_forced_speak_prompt,
    build_consensus_check_prompt,
    build_summary_prompt,
    format_transcript,
    format_experts_info,
)
from app.services.session_service import (
    save_message, complete_session, fail_session,
)
from app.exceptions import LLMAPIException


# ═══════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════

class DiscussionState(TypedDict):
    session_id: str
    topic: str
    host: dict              # {id, name, title, stance, avatar, color}
    experts: list[dict]     # [{id, name, title, stance, avatar, color}]
    all_guests: list[dict]  # host + experts combined
    current_phase: str
    current_round: int
    last_speaker_id: str
    messages: Annotated[list[dict], operator.add]
    sse_events: Annotated[list[str], operator.add]
    consensus_points: Annotated[list[str], operator.add]
    divergence_points: Annotated[list[str], operator.add]
    expert_status: dict     # {expert_id: {state, focus}}
    total_rounds: int
    sequence: int
    error: str | None


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _msg_dict(msg) -> dict:
    return {
        "id": msg.id, "session_id": msg.session_id,
        "phase": msg.phase, "round": msg.round,
        "speaker_id": msg.speaker_id, "speaker_name": msg.speaker_name,
        "content": msg.content, "sequence": msg.sequence,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }

def _get_db(config: RunnableConfig | None) -> AsyncSession | None:
    if config and "configurable" in config:
        return config["configurable"].get("db")
    return None

def _parse_json(raw: str, default: dict) -> dict:
    import re
    try: return json.loads(raw)
    except: pass
    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        try: return json.loads(m.group())
        except: pass
    return default


# ═══════════════════════════════════════════════════════
# Node: INIT
# ═══════════════════════════════════════════════════════

async def init_node(state: DiscussionState, config: RunnableConfig | None = None) -> dict:
    experts = state["experts"]
    host = state["host"]
    all_guests = [host] + experts

    # Initial expert status: all idle
    status = {}
    for e in experts:
        status[e["id"]] = {"state": "idle", "focus": "等待讨论开始..."}

    return {
        "all_guests": all_guests,
        "current_phase": "INIT",
        "current_round": 0,
        "last_speaker_id": "",
        "sequence": 0,
        "expert_status": status,
        "consensus_points": [],
        "divergence_points": [],
        "sse_events": [
            _sse("connected", {
                "session_id": state["session_id"],
                "topic": state["topic"],
                "message": "讨论即将开始...",
            }),
            _sse("expert_status", {"status": status}),
        ],
        "error": None,
    }


# ═══════════════════════════════════════════════════════
# Node: HOST_INTRO
# ═══════════════════════════════════════════════════════

async def host_intro_node(state: DiscussionState, config: RunnableConfig | None = None) -> dict:
    llm = get_llm_service()
    db = _get_db(config)
    topic = state["topic"]
    experts = state["experts"]
    host = state["host"]
    sid = state["session_id"]
    seq = state["sequence"] + 1

    # Update host status
    status = dict(state["expert_status"])
    sse_events = [_sse("phase_start", {"phase": "opening", "round": 0, "label": "主持人开场"})]
    sse_events.append(_sse("expert_status", {"status": {**status, "__host__": {"state": "speaking", "focus": "准备开场"}}}))

    experts_info = format_experts_info(experts)

    try:
        text = await llm.generate(
            system_prompt=HOST_SYSTEM_PROMPT,
            user_message=build_opening_prompt(topic, experts_info),
            temperature=0.8, max_tokens=300,
        )
    except LLMAPIException:
        return {"error": "HOST_INTRO failed", "sse_events": sse_events}

    if db:
        msg = await save_message(db, sid, "opening", 0, host["id"], host["name"], text, seq)
        md = _msg_dict(msg)
    else:
        md = {"id": "intro", "session_id": sid, "phase": "opening", "round": 0,
              "speaker_id": host["id"], "speaker_name": host["name"],
              "content": text, "sequence": seq, "created_at": ""}

    sse_events.append(_sse("moderator_opening", md))
    # Reset host status
    sse_events.append(_sse("expert_status", {"status": {**status, "__host__": {"state": "idle", "focus": "聆听专家发言"}}}))

    return {
        "current_phase": "HOST_INTRO",
        "last_speaker_id": host["id"],
        "sequence": seq,
        "messages": [md],
        "sse_events": sse_events,
    }


# ═══════════════════════════════════════════════════════
# Node: AUTONOMOUS_DISCUSSION — core dynamic round
# ═══════════════════════════════════════════════════════

async def autonomous_discussion_node(state: DiscussionState, config: RunnableConfig | None = None) -> dict:
    """
    One round of autonomous discussion:
    1. All experts concurrently decide if they want to speak
    2. Pick the one with highest urgency
    3. That expert speaks (1-2 sentences)
    4. Emit status updates
    5. Periodically: host follow-up or consensus check
    """
    llm = get_llm_service()
    db = _get_db(config)
    topic = state["topic"]
    experts = state["experts"]
    host = state["host"]
    sid = state["session_id"]
    seq = state["sequence"] + 1
    all_msgs = list(state["messages"])
    round_num = state["current_round"]
    last_speaker = state["last_speaker_id"]

    status = dict(state["expert_status"])
    sse_events = []

    # ── Step 1: All experts concurrently decide ──────────
    transcript = format_transcript(all_msgs, last_n=15)  # More context

    # Update status: all non-last-speaker experts → preparing
    for e in experts:
        if e["id"] != last_speaker:
            status[e["id"]] = {"state": "preparing", "focus": "分析讨论中..."}

    sse_events.append(_sse("expert_status", {"status": dict(status)}))

    # Concurrent LLM calls for decision
    async def _ask_expert(e: dict) -> dict | None:
        try:
            sys_prompt = build_expert_system_prompt(e["name"], e["title"], e["stance"])
            raw = await llm.generate(
                system_prompt=sys_prompt,
                user_message=build_expert_decide_prompt(
                    e["name"], e["title"], e["stance"], topic, transcript,
                ),
                temperature=0.7, max_tokens=250,
            )
            decision = _parse_json(raw, {"should_speak": False, "urgency": 0, "focus": "", "content": ""})
            return {"expert": e, "decision": decision}
        except LLMAPIException:
            return None

    results = await asyncio.gather(*[_ask_expert(e) for e in experts])

    # ── Step 2: Pick highest urgency expert ──────────────
    candidates = []
    for r in results:
        if r and r["decision"].get("should_speak") and r["decision"].get("urgency", 0) >= 5:
            candidates.append(r)

    # Sort by urgency (descending), take top 2
    candidates.sort(key=lambda x: x["decision"].get("urgency", 0), reverse=True)
    speakers = candidates[:2]  # Up to 2 speakers per round

    # Update statuses
    for r in (results or []):
        if r:
            eid = r["expert"]["id"]
            focus = r["decision"].get("focus", "")[:30]
            status[eid] = {"state": "ready" if r["decision"].get("should_speak") else "idle",
                          "focus": focus or ("准备发言" if r["decision"].get("should_speak") else "聆听中")}

    all_md = []
    current_seq = seq

    if speakers:
        for speaker_idx, chosen in enumerate(speakers):
            expert = chosen["expert"]
            pre_content = chosen["decision"].get("content", "")

            sys_prompt = build_expert_system_prompt(expert["name"], expert["title"], expert["stance"])
            if not pre_content or len(pre_content.strip()) < 5:
                user_prompt = build_expert_forced_speak_prompt(
                    expert["name"], expert["title"], expert["stance"],
                    topic, transcript, "请分享你的观点",
                )
            else:
                user_prompt = build_expert_forced_speak_prompt(
                    expert["name"], expert["title"], expert["stance"],
                    topic, transcript, pre_content,
                )

            status[expert["id"]] = {"state": "speaking", "focus": "发言中..."}
            sse_events.append(_sse("expert_status", {"status": dict(status)}))

            msg_id = f"auto-{round_num}-{current_seq}"
            sse_events.append(_sse("message_start", {
                "id": msg_id, "session_id": sid,
                "phase": "free_discussion", "round": round_num + 1,
                "speaker_id": expert["id"], "speaker_name": expert["name"],
            }))

            full_content = ""
            try:
                async for chunk in llm.generate_stream(
                    system_prompt=sys_prompt,
                    user_message=user_prompt,
                    temperature=0.85, max_tokens=300,
                ):
                    full_content += chunk
                    sse_events.append(_sse("message_chunk", {
                        "id": msg_id, "content_delta": chunk,
                        "speaker_id": expert["id"],
                    }))
            except LLMAPIException:
                full_content = pre_content or "（发言生成失败）"
                sse_events.append(_sse("message_chunk", {
                    "id": msg_id, "content_delta": full_content,
                    "speaker_id": expert["id"],
                }))

            content = full_content.strip()
            if db and content:
                msg = await save_message(db, sid, "free_discussion", round_num + 1,
                                         expert["id"], expert["name"], content, current_seq)
                md = _msg_dict(msg)
                current_seq += 1
            else:
                md = {"id": msg_id, "session_id": sid, "phase": "free_discussion",
                      "round": round_num + 1, "speaker_id": expert["id"], "speaker_name": expert["name"],
                      "content": content, "sequence": current_seq, "created_at": ""}
                current_seq += 1

            sse_events.append(_sse("free_discussion", md))
            all_md.append(md)
            status[expert["id"]] = {"state": "idle", "focus": "已发言，继续聆听"}
            sse_events.append(_sse("expert_status", {"status": dict(status)}))

        # ── Host proactively connects ideas every 5 rounds ──
        if (state["current_round"] + 1) % 5 == 0 and len(all_msgs + all_md) >= 3:
            try:
                connect_text = await llm.generate(
                    system_prompt=HOST_SYSTEM_PROMPT,
                    user_message=build_connect_prompt(
                        topic, all_msgs + all_md,
                        list(state.get("consensus_points", [])),
                        list(state.get("divergence_points", [])),
                    ),
                    temperature=0.7, max_tokens=200,
                )
                if connect_text and connect_text.strip():
                    status["__host__"] = {"state": "speaking", "focus": "串联观点中..."}
                    sse_events.append(_sse("expert_status", {"status": dict(status)}))
                    sse_events.append(_sse("moderator_connect", {
                        "id": f"host-connect-{round_num}",
                        "session_id": sid, "phase": "free_discussion",
                        "round": round_num + 1,
                        "speaker_id": host["id"], "speaker_name": host["name"],
                        "content": connect_text.strip(),
                    }))
                    status.pop("__host__", None)
                    sse_events.append(_sse("expert_status", {"status": dict(status)}))
            except Exception:
                pass

        # ── Consensus check every ~3 rounds ──────────
        new_consensus = []
        new_divergence = []
        if (state["current_round"] + 1) % 3 == 0:
            try:
                check_prompt = build_consensus_check_prompt(
                    topic, format_transcript(all_msgs + all_md, last_n=15),
                    list(state.get("consensus_points", [])),
                    list(state.get("divergence_points", [])),
                )
                raw = await llm.generate(
                    system_prompt="你是专业讨论分析师。只用JSON回复。",
                    user_message=check_prompt, temperature=0.3, max_tokens=300,
                )
                result = _parse_json(raw, {"new_consensus": [], "new_divergence": []})
                new_consensus = result.get("new_consensus", [])
                new_divergence = result.get("new_divergence", [])
                if new_consensus or new_divergence:
                    sse_events.append(_sse("consensus_update", {
                        "new_consensus": new_consensus,
                        "new_divergence": new_divergence,
                        "all_consensus": list(state.get("consensus_points", [])) + new_consensus,
                        "all_divergence": list(state.get("divergence_points", [])) + new_divergence,
                    }))
            except Exception:
                pass

        return {
            "current_phase": "AUTONOMOUS_DISCUSSION",
            "current_round": state["current_round"] + 1,
            "last_speaker_id": speakers[-1]["expert"]["id"],
            "sequence": current_seq,
            "messages": all_md,
            "consensus_points": new_consensus,
            "divergence_points": new_divergence,
            "sse_events": sse_events,
            "expert_status": dict(status),
        }

    else:
        # ── No one wants to speak → Host intervenes ────
        for eid in status:
            status[eid] = {"state": "idle", "focus": status[eid].get("focus", "等待中")}
        sse_events.append(_sse("expert_status", {"status": dict(status)}))

        try:
            raw = await llm.generate(
                system_prompt=HOST_SYSTEM_PROMPT,
                user_message=build_host_followup_prompt(topic, transcript),
                temperature=0.7, max_tokens=200,
            )
            decision = _parse_json(raw, {"action": "advance", "target": "", "content": "让我们换个角度来看这个问题。"})
        except LLMAPIException:
            decision = {"action": "advance", "target": "", "content": "请继续讨论。"}

        action = decision.get("action", "advance")
        content = decision.get("content", "")
        target = decision.get("target", "")

        if action == "summarize":
            # Signal to move to summary phase
            return {
                "current_phase": "AUTONOMOUS_DISCUSSION",
                "current_round": state["total_rounds"] + 1,  # triggers exit
                "last_speaker_id": host["id"],
                "sse_events": sse_events,
            }

        # Host follow-up or advance
        if db and content:
            msg = await save_message(db, sid, "free_discussion", round_num + 1,
                                     host["id"], host["name"], content, seq)
            md = _msg_dict(msg)
        elif content:
            md = {"id": f"host-{round_num}", "session_id": sid, "phase": "free_discussion",
                  "round": round_num + 1, "speaker_id": host["id"], "speaker_name": host["name"],
                  "content": content, "sequence": seq, "created_at": ""}
        else:
            md = None

        if md:
            sse_events.append(_sse("moderator_connect", md))
            return {
                "current_phase": "AUTONOMOUS_DISCUSSION",
                "current_round": state["current_round"] + 1,  # Advance round
                "last_speaker_id": host["id"],
                "sequence": seq,
                "messages": [md],
                "sse_events": sse_events,
            }
        else:
            return {
                "current_phase": "AUTONOMOUS_DISCUSSION",
                "current_round": state["current_round"] + 1,  # Advance round
                "sse_events": sse_events,
            }


# ═══════════════════════════════════════════════════════
# Node: HOST_SUMMARY
# ═══════════════════════════════════════════════════════

async def host_summary_node(state: DiscussionState, config: RunnableConfig | None = None) -> dict:
    llm = get_llm_service()
    db = _get_db(config)
    topic = state["topic"]
    host = state["host"]
    sid = state["session_id"]
    seq = state["sequence"] + 1
    all_msgs = list(state["messages"])
    consensus = list(state.get("consensus_points", []))
    divergence = list(state.get("divergence_points", []))

    sse_events = [_sse("phase_start", {"phase": "summary", "round": 0, "label": "主持人总结"})]

    transcript = format_transcript(all_msgs, last_n=999)

    try:
        text = await llm.generate(
            system_prompt=HOST_SYSTEM_PROMPT,
            user_message=build_summary_prompt(topic, transcript, consensus, divergence),
            temperature=0.7, max_tokens=800,
        )
    except LLMAPIException:
        text = "感谢各位嘉宾的深入讨论。由于技术原因，本次无法生成完整总结。"

    if db:
        msg = await save_message(db, sid, "summary", 0, host["id"], host["name"], text, seq)
        md = _msg_dict(msg)
        await complete_session(db, sid)
    else:
        md = {"id": "summary", "session_id": sid, "phase": "summary", "round": 0,
              "speaker_id": host["id"], "speaker_name": host["name"],
              "content": text, "sequence": seq, "created_at": ""}

    sse_events.append(_sse("moderator_summary", md))
    sse_events.append(_sse("session_end", {
        "session_id": sid, "topic": topic,
        "message_count": len(all_msgs) + 1,
        "consensus": consensus, "divergence": divergence,
    }))
    sse_events.append(_sse("done", {"message": "[DONE]"}))

    return {
        "current_phase": "HOST_SUMMARY",
        "sequence": seq,
        "messages": [md],
        "sse_events": sse_events,
    }


# ═══════════════════════════════════════════════════════
# Routing
# ═══════════════════════════════════════════════════════

def after_init(state: DiscussionState) -> str:
    return "host_intro" if not state.get("error") else "END"

def after_host_intro(state: DiscussionState) -> str:
    return "autonomous_discussion" if not state.get("error") else "END"

def after_autonomous(state: DiscussionState) -> str:
    if state.get("error"):
        return "END"
    if state["current_round"] >= state["total_rounds"]:
        return "host_summary"
    return "autonomous_discussion"


# ═══════════════════════════════════════════════════════
# Graph Builder
# ═══════════════════════════════════════════════════════

def build_discussion_graph() -> StateGraph:
    builder = StateGraph(DiscussionState)

    builder.add_node("init", init_node)
    builder.add_node("host_intro", host_intro_node)
    builder.add_node("autonomous_discussion", autonomous_discussion_node)
    builder.add_node("host_summary", host_summary_node)

    builder.set_entry_point("init")

    builder.add_conditional_edges("init", after_init, {"host_intro": "host_intro", "END": END})
    builder.add_conditional_edges("host_intro", after_host_intro, {"autonomous_discussion": "autonomous_discussion", "END": END})
    builder.add_conditional_edges("autonomous_discussion", after_autonomous, {
        "autonomous_discussion": "autonomous_discussion",
        "host_summary": "host_summary",
        "END": END,
    })
    builder.add_edge("host_summary", END)

    return builder.compile()


# ═══════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════

async def run_discussion(
    db: AsyncSession,
    session_id: str,
    topic: str,
    host: dict,
    experts: list[dict],
):
    """Run autonomous roundtable and yield SSE events via astream."""
    graph = build_discussion_graph()

    initial_state: DiscussionState = {
        "session_id": session_id,
        "topic": topic,
        "host": host,
        "experts": experts,
        "all_guests": [],
        "current_phase": "INIT",
        "current_round": 0,
        "last_speaker_id": "",
        "messages": [],
        "sse_events": [],
        "consensus_points": [],
        "divergence_points": [],
        "expert_status": {},
        "total_rounds": settings.FREE_DISCUSSION_ROUNDS + 2,  # core discussion rounds
        "sequence": 0,
        "error": None,
    }

    runtime_config: RunnableConfig = {"configurable": {"db": db}}

    try:
        async for chunk in graph.astream(
            initial_state,
            stream_mode="updates",
            config=runtime_config,
        ):
            for _node_name, update in chunk.items():
                for sse_str in update.get("sse_events", []):
                    yield sse_str

                if update.get("error"):
                    await fail_session(db, session_id)
                    yield _sse("error", {"code": "DISCUSSION_ERROR", "message": update["error"]})
                    return

    except Exception as e:
        await fail_session(db, session_id)
        yield _sse("error", {"code": "DISCUSSION_ERROR", "message": str(e)})


async def _run_consensus_check(
    db, session_id: str, topic: str,
    recent_msgs: list[dict],
    existing_c: list[str], existing_d: list[str],
) -> list[str]:
    """Run consensus check and return SSE events."""
    if not recent_msgs:
        return []
    llm = get_llm_service()
    transcript = format_transcript(recent_msgs, last_n=6)
    try:
        raw = await llm.generate(
            system_prompt="你是一位专业讨论分析师。只输出JSON。",
            user_message=build_consensus_check_prompt(topic, transcript, existing_c, existing_d),
            temperature=0.3, max_tokens=300,
        )
        result = _parse_json(raw, {"new_consensus": [], "new_divergence": []})
        nc = result.get("new_consensus", [])
        nd = result.get("new_divergence", [])
    except LLMAPIException:
        return []

    if nc or nd:
        return [_sse("consensus_update", {
            "new_consensus": nc,
            "new_divergence": nd,
            "all_consensus": existing_c + nc,
            "all_divergence": existing_d + nd,
        })]
    return []
