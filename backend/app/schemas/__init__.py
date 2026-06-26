from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.guest import GuestResponse
from app.schemas.message import MessageResponse
from app.schemas.session import (
    SessionCreate,
    SessionBrief,
    SessionDetail,
    GuestBrief,
)

# Resolve forward references: SessionDetail -> MessageResponse
SessionDetail.model_rebuild()

__all__ = [
    "ApiResponse",
    "PaginatedData",
    "GuestResponse",
    "MessageResponse",
    "SessionCreate",
    "SessionBrief",
    "SessionDetail",
    "GuestBrief",
]
