"""Session CRUD service."""

import json
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.session import Session
from app.models.message import Message


async def create_session(db: AsyncSession, topic: str, guest_ids: list[str]) -> Session:
    """Create session with preset guest IDs (backward compat)."""
    session = Session(topic=topic, guest_ids=json.dumps(guest_ids, ensure_ascii=False))
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def create_session_with_guests(db: AsyncSession, topic: str, guest_ids: list[str], guests_json: str) -> Session:
    """Create session with full custom guest data."""
    session = Session(topic=topic, guest_ids=guests_json)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession, page: int = 1, page_size: int = 20, status_filter: str | None = None
) -> tuple[list[Session], int]:
    stmt = select(Session)
    count_stmt = select(func.count(Session.id))

    if status_filter and status_filter != "all":
        stmt = stmt.where(Session.status == status_filter)
        count_stmt = count_stmt.where(Session.status == status_filter)
    else:
        # Default: exclude 'error' sessions from general listing
        stmt = stmt.where(Session.status != "error")
        count_stmt = count_stmt.where(Session.status != "error")

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        stmt.order_by(Session.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_session_message_count(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        select(func.count(Message.id)).where(Message.session_id == session_id)
    )
    return result.scalar() or 0


async def get_session_messages(db: AsyncSession, session_id: str) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.sequence)
    )
    return list(result.scalars().all())


async def save_message(
    db: AsyncSession, session_id: str, phase: str, round: int,
    speaker_id: str, speaker_name: str, content: str, sequence: int,
) -> Message:
    message = Message(
        session_id=session_id, phase=phase, round=round,
        speaker_id=speaker_id, speaker_name=speaker_name,
        content=content, sequence=sequence,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def complete_session(db: AsyncSession, session_id: str) -> None:
    from datetime import datetime, timezone
    session = await get_session(db, session_id)
    if session:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def fail_session(db: AsyncSession, session_id: str) -> None:
    session = await get_session(db, session_id)
    if session:
        session.status = "error"
        await db.commit()


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    result = await db.execute(delete(Session).where(Session.id == session_id))
    await db.commit()
    return result.rowcount > 0
