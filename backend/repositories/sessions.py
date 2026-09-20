import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Message, NegotiationSession


async def get_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> NegotiationSession | None:
    result = await db.execute(
        select(NegotiationSession)
        .options(
            selectinload(NegotiationSession.state),
            selectinload(NegotiationSession.result),
        )
        .where(NegotiationSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(result.scalars().all())
