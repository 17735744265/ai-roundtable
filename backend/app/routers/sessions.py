"""Session router — CRUD + topic-based guest generation."""

import json
import re
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.session import (
    SessionCreate, SessionBrief, SessionDetail, GuestBrief,
    GeneratedGuest, GuestGenerateResponse,
)
from app.schemas.message import MessageResponse
from app.exceptions import NotFoundException, ConflictException, ValidationException
from app.services import session_service
from app.services.llm_service import get_llm_service

router = APIRouter()

from pathlib import Path
_guests_path = Path(__file__).parent.parent / "data" / "guests.json"
with open(_guests_path, "r", encoding="utf-8") as f:
    GUESTS_MAP: dict = {g["id"]: g for g in json.load(f)}

COLORS_POOL = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#F97316"]


# ── Topic-based Guest Generation ──────────────────────

class GuestGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)

@router.post("/discussion/generate-guests", response_model=ApiResponse[GuestGenerateResponse])
async def generate_guests(body: GuestGenerateRequest):
    """Generate a relevant host + expert lineup based on the topic."""
    llm = get_llm_service()
    prompt = f"""为以下话题策划AI圆桌讨论阵容。

话题：{body.topic}

生成1位主持人和5-6位专家。要求：
- 专家背景严格围绕话题展开，不同视角互补（支持/质疑/中立/跨界）
- 每位专家：name(真实感姓名)、title(具体职业)、stance(15-25字立场)、avatar(1个相关emoji)
- 分配不同颜色：{json.dumps(COLORS_POOL[:6])}

JSON格式回复：
```json
{{"host":{{"name":"...","title":"...","stance":"...","avatar":"🎤","color":"..."}},
"experts":[{{"name":"...","title":"...","stance":"...","avatar":"...","color":"..."}}]}}
```
只输出JSON。"""

    try:
        raw = await llm.generate(
            system_prompt="你是专业圆桌策划人。只用JSON回复。",
            user_message=prompt, temperature=0.9, max_tokens=1000,
        )
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match: raise ValueError("No JSON found")
        data = json.loads(match.group())

        host = data["host"]; host["id"] = "moderator"; host.setdefault("avatar", "🎤")
        experts = []
        for i, e in enumerate(data["experts"][:6]):
            e["id"] = f"gen_{i}"; e.setdefault("avatar", ["💼","🔬","📊","🎨","⚙️","🛡️"][i])
            experts.append(GeneratedGuest(**e))

        return ApiResponse(data=GuestGenerateResponse(host=GeneratedGuest(**host), experts=experts))
    except Exception as e:
        raise ValidationException(f"生成失败: {str(e)}")


# ── Session CRUD ──────────────────────────────────────

@router.post("/discussion/start", response_model=ApiResponse[SessionDetail], status_code=201)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new discussion session. Supports preset IDs or AI-generated guests."""

    host = GeneratedGuest(id="moderator", name="主持人", title="圆桌讨论主持人",
                          stance="保持中立，引导深度讨论", avatar="🎤", color="#F59E0B")
    experts = []

    if body.generated_guests:
        # AI-generated guests mode
        if len(body.generated_guests) < 3:
            raise ValidationException("至少选择 3 位嘉宾")
        experts = body.generated_guests
    else:
        # Preset guest IDs mode
        if len(body.guest_ids) < 3:
            raise ValidationException("至少选择 3 位嘉宾")
        for gid in body.guest_ids:
            if gid not in GUESTS_MAP:
                raise ValidationException(f"无效的嘉宾 ID: {gid}")
        if len(set(body.guest_ids)) != len(body.guest_ids):
            raise ValidationException("嘉宾 ID 不能重复")
        for i, gid in enumerate(body.guest_ids):
            g = GUESTS_MAP[gid]
            experts.append(GeneratedGuest(
                id=gid, name=g["name"], title=g.get("description", ""),
                stance=g.get("personality", ""), avatar=g["avatar"],
                color=COLORS_POOL[i % len(COLORS_POOL)],
            ))

    all_guests = [host] + experts
    guests_json = json.dumps([g.model_dump() for g in all_guests], ensure_ascii=False)
    session = await session_service.create_session_with_guests(
        db, body.topic, [g.id for g in all_guests], guests_json
    )

    return ApiResponse(
        data=SessionDetail(
            id=session.id, topic=session.topic,
            guests=[GuestBrief(id=g.id, name=g.name, avatar=g.avatar, title=g.title, color=g.color) for g in all_guests],
            status=session.status, messages=[],
            created_at=session.created_at, completed_at=session.completed_at,
        )
    )


@router.get("/discussions", response_model=ApiResponse[PaginatedData[SessionBrief]])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status_filter: str = Query("", description="Filter: active | completed | error | all"),
    db: AsyncSession = Depends(get_db),
):
    """List discussions with optional status filter."""
    sessions, total = await session_service.list_sessions(db, page, page_size, status_filter or None)

    items = []
    for s in sessions:
        guests = _parse_guests(s.guest_ids)
        msg_count = await session_service.get_session_message_count(db, s.id)
        items.append(SessionBrief(
            id=s.id, topic=s.topic, guests=guests,
            status=s.status, message_count=msg_count,
            created_at=s.created_at,
        ))

    return ApiResponse(
        data=PaginatedData(items=items, total=total, page=page, page_size=page_size)
    )


@router.get("/discussions/{session_id}", response_model=ApiResponse[SessionDetail])
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await session_service.get_session(db, session_id)
    if not session:
        raise NotFoundException()

    guests = _parse_guests(session.guest_ids)
    messages = await session_service.get_session_messages(db, session_id)

    return ApiResponse(
        data=SessionDetail(
            id=session.id, topic=session.topic, guests=guests,
            status=session.status,
            messages=[MessageResponse.model_validate(m) for m in messages],
            created_at=session.created_at, completed_at=session.completed_at,
        )
    )


@router.delete("/discussions/{session_id}", response_model=ApiResponse)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await session_service.get_session(db, session_id)
    if not session:
        raise NotFoundException()
    if session.status == "active":
        raise ConflictException()
    await session_service.delete_session(db, session_id)
    return ApiResponse(message="删除成功")


# ── Helpers ──────────────────────────────────────────

def _parse_guests(raw: str) -> list[GuestBrief]:
    """Parse guest JSON from DB. Handle both old (preset IDs) and new (full object) formats."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    guests = []
    for item in data:
        if isinstance(item, str):
            # Old format: just guest ID → look up
            g = GUESTS_MAP.get(item, {"name": item, "avatar": "👤"})
            guests.append(GuestBrief(id=item, name=g.get("name", item), avatar=g.get("avatar", "👤"), title="", color="#94A3B8"))
        elif isinstance(item, dict):
            guests.append(GuestBrief(
                id=item.get("id", ""),
                name=item.get("name", ""),
                avatar=item.get("avatar", "👤"),
                title=item.get("title", ""),
                color=item.get("color", "#94A3B8"),
            ))
    return guests
