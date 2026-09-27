import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import SessionMetricEvent, SessionState


async def get_session_state(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> SessionState | None:
    return await db.get(SessionState, session_id)


async def get_latest_metric_event(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> SessionMetricEvent | None:
    result = await db.execute(
        select(SessionMetricEvent)
        .where(SessionMetricEvent.session_id == session_id)
        .order_by(
            SessionMetricEvent.turn_count.desc(),
            SessionMetricEvent.created_at.desc(),
            SessionMetricEvent.id.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
