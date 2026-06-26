"""Session schemas — including dynamic guest generation."""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Dynamic Guest Generation ──────────────────────────

class GuestGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200, description="讨论话题")
    expert_count: int = Field(default=3, ge=2, le=5, description="专家人数(2-5)")

class GeneratedGuest(BaseModel):
    id: str          # e.g. "expert_0"
    name: str        # e.g. "张明"
    title: str       # e.g. "资深产品战略顾问"
    stance: str      # e.g. "支持远程办公，强调效率提升"
    color: str       # e.g. "#3B82F6"
    avatar: str      # e.g. "💼"

class GuestGenerateResponse(BaseModel):
    host: GeneratedGuest           # 主持人
    experts: list[GeneratedGuest]  # 专家列表


# ── Session CRUD ──────────────────────────────────────

class SessionCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    guest_ids: list[str] = Field(default=[], description="预设嘉宾ID列表(3-6位)")
    generated_guests: list[GeneratedGuest] = Field(default=[], description="AI生成的嘉宾对象列表")


class GuestBrief(BaseModel):
    id: str
    name: str
    avatar: str
    title: str = ""
    color: str = "#94A3B8"


class SessionBrief(BaseModel):
    id: str
    topic: str
    guests: list[GuestBrief]
    status: str
    message_count: int = 0
    created_at: datetime


class SessionDetail(BaseModel):
    id: str
    topic: str
    guests: list[GuestBrief]
    status: str
    messages: list["MessageResponse"] = []
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True
