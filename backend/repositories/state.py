import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from models import SessionState


async def get_session_state(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> SessionState | None:
    return await db.get(SessionState, session_id)
