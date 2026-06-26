"""Message ORM model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.session import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    phase: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # opening | statements | free_discussion | summary
    round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    speaker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, speaker={self.speaker_name}, "
            f"phase={self.phase}, seq={self.sequence})>"
        )
