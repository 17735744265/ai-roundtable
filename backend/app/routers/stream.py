"""SSE stream router — GET /api/discussion/{session_id}/stream"""

import json
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, async_session
from app.services.discussion_orchestrator import run_discussion
from app.services.session_service import get_session, get_session_messages
from app.exceptions import NotFoundException

router = APIRouter()

HEARTBEAT_INTERVAL = 15  # seconds

# Track sessions with active discussion runs (prevent duplicate starts)
_active_runs: set[str] = set()


def _sse(event: str, data: dict) -> str:
    """Format a dict as an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _msg_to_dict(msg) -> dict:
    """Convert Message ORM to dict."""
    return {
        "id": msg.id,
        "session_id": msg.session_id,
        "phase": msg.phase,
        "round": msg.round,
        "speaker_id": msg.speaker_id,
        "speaker_name": msg.speaker_name,
        "content": msg.content,
        "sequence": msg.sequence,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }


@router.get("/discussion/{session_id}/stream")
async def stream_discussion(session_id: str, db: AsyncSession = Depends(get_db)):
    """SSE endpoint: real-time stream for active sessions, replay for completed ones."""
    session = await get_session(db, session_id)
    if not session:
        raise NotFoundException("讨论会话不存在")

    guests_data = json.loads(session.guest_ids)
    topic = session.topic

    # Parse guests: new format is [host_obj, expert1_obj, expert2_obj, ...]
    host = {}
    experts = []
    if isinstance(guests_data, list) and len(guests_data) > 0:
        if isinstance(guests_data[0], dict):
            host = guests_data[0]
            experts = guests_data[1:]
        else:
            # Old format: list of guest IDs — backward compat
            guest_ids = guests_data
            host = {"id": "moderator", "name": "主持人", "title": "圆桌主持人", "stance": "中立", "avatar": "🎤", "color": "#F59E0B"}
            experts = []
            from pathlib import Path
            _guests_path = Path(__file__).parent.parent / "data" / "guests.json"
            with open(_guests_path, "r", encoding="utf-8") as f:
                old_guests = {g["id"]: g for g in json.load(f)}
            for i, gid in enumerate(guest_ids):
                og = old_guests.get(gid, {"id": gid, "name": gid, "avatar": "👤"})
                experts.append({"id": gid, "name": og.get("name", gid), "title": og.get("description", ""), "stance": og.get("personality", ""), "avatar": og.get("avatar", "👤"), "color": ""})

    # Check if discussion already has content or is running (reconnection)
    existing_messages = await get_session_messages(db, session_id)

    if session.status == "active" and len(existing_messages) == 0 and session_id not in _active_runs:
        # ── Live mode: first connection, run discussion ────
        _active_runs.add(session_id)
        return _live_stream(session_id, topic, host, experts)

    else:
        # ── Replay mode: reconnection or completed session ──
        return await _replay_stream(db, session_id, topic, host, experts)


# ── Live Streaming ────────────────────────────────────────────

def _live_stream(session_id: str, topic: str, host: dict, experts: list[dict]) -> StreamingResponse:
    """Stream a live discussion with heartbeat. Locks via _active_runs."""

    async def event_generator():
        try:
            async with async_session() as stream_db:
                queue: asyncio.Queue[str | None] = asyncio.Queue()

                async def run_discussion_task():
                    try:
                        async for sse_str in run_discussion(
                            stream_db, session_id, topic, host, experts
                        ):
                            await queue.put(sse_str)
                    except Exception as e:
                        await queue.put(
                            _sse("error", {
                                "code": "STREAM_ERROR",
                                "message": str(e),
                            })
                        )
                    finally:
                        await queue.put(None)  # Sentinel: discussion done

                async def heartbeat_task():
                    while True:
                        await asyncio.sleep(HEARTBEAT_INTERVAL)
                        await queue.put(": ping\n\n")

                discussion = asyncio.create_task(run_discussion_task())
                heartbeat = asyncio.create_task(heartbeat_task())

                try:
                    while True:
                        item = await queue.get()
                        if item is None:
                            await asyncio.sleep(0.3)
                            break
                        yield item
                finally:
                    heartbeat.cancel()
                    discussion.cancel()
                    try: await heartbeat
                    except asyncio.CancelledError: pass
                    try: await discussion
                    except asyncio.CancelledError: pass
        finally:
            _active_runs.discard(session_id)
            # If session still active with 0 messages, mark as error (abandoned)
            try:
                from app.database import async_session as _as
                from app.services.session_service import get_session, fail_session, get_session_message_count
                async with _as() as cleanup_db:
                    s = await get_session(cleanup_db, session_id)
                    if s and s.status == "active":
                        msg_count = await get_session_message_count(cleanup_db, session_id)
                        if msg_count == 0:
                            await fail_session(cleanup_db, session_id)
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Replay Streaming (for completed/error sessions) ────────────

async def _replay_stream(
    db: AsyncSession, session_id: str, topic: str, host: dict, experts: list[dict]
) -> StreamingResponse:
    """Replay all saved messages as an SSE stream — prevents 409 loops."""

    messages = await get_session_messages(db, session_id)

    async def event_generator():
        # Connected
        yield _sse("connected", {
            "session_id": session_id,
            "topic": topic,
            "message": "加载已完成的讨论...",
        })

        if not messages:
            yield _sse("done", {"message": "[DONE]"})
            return

        # Replay phase by phase
        seen_phases: set[str] = set()
        current_phase = None

        for msg in messages:
            msg_dict = _msg_to_dict(msg)

            # Emit phase_start once per phase
            if msg.phase != current_phase:
                current_phase = msg.phase
                round_num = msg.round if msg.phase == "free_discussion" else (1 if msg.phase == "statements" else 0)
                yield _sse("phase_start", {"phase": msg.phase, "round": round_num})

            # Emit appropriate event per phase
            event_map = {
                "opening": "moderator_opening",
                "statements": "guest_statement",
                "free_discussion": "free_discussion",
                "summary": "moderator_summary",
            }
            event_type = event_map.get(msg.phase, "guest_statement")
            yield _sse(event_type, msg_dict)

        # Phase end for the last phase
        if current_phase and current_phase in ("statements", "free_discussion"):
            yield _sse("phase_end", {"phase": current_phase})

        yield _sse("session_end", {
            "session_id": session_id,
            "topic": topic,
            "message_count": len(messages),
        })
        yield _sse("done", {"message": "[DONE]"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
