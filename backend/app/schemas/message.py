"""Message schemas."""

from datetime import datetime
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: str
    session_id: str
    phase: str
    round: int
    speaker_id: str
    speaker_name: str
    content: str
    sequence: int
    created_at: datetime

    class Config:
        from_attributes = True
