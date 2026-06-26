"""Session ORM model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    guest_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array string
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active | completed | error
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages = relationship("Message", back_populates="session", order_by="Message.sequence")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, topic={self.topic[:30]}..., status={self.status})>"
