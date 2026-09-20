import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.sessions import get_messages, get_session
from schemas import (
    CreateSessionRequest,
    MessageResponse,
    SessionResponse,
    SessionResultResponse,
    SessionStateResponse,
)
from services.negotiation import (
    complete_negotiation_session,
    create_negotiation_session,
)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        negotiation_session, initial_message = (
            await create_negotiation_session(
                db,
                request.scenario_id if request else None,
            )
        )
    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return SessionResponse(
        session_id=negotiation_session.id,
        status=negotiation_session.status,
        scenario_id=negotiation_session.scenario_id,
        state=SessionStateResponse(
            metrics=negotiation_session.state.metrics,
            turn_count=negotiation_session.state.turn_count,
            detected_tactics=negotiation_session.state.detected_tactics,
            coach_message=negotiation_session.state.coach_message,
        ),
        result=None,
        messages=[
            MessageResponse(
                role=initial_message.role,
                content=initial_message.content,
                created_at=initial_message.created_at,
            )
        ],
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    messages = await get_messages(db, session_id)

    return SessionResponse(
        session_id=negotiation_session.id,
        status=negotiation_session.status,
        scenario_id=negotiation_session.scenario_id,
        state=(
            SessionStateResponse(
                metrics=negotiation_session.state.metrics,
                turn_count=negotiation_session.state.turn_count,
                detected_tactics=negotiation_session.state.detected_tactics,
                coach_message=negotiation_session.state.coach_message,
            )
            if negotiation_session.state
            else None
        ),
        result=(
            SessionResultResponse(
                final_score=negotiation_session.result.final_score,
                outcome=negotiation_session.result.outcome,
                final_metrics=negotiation_session.result.final_metrics,
                strengths=negotiation_session.result.strengths,
                mistakes=negotiation_session.result.mistakes,
                recommendations=negotiation_session.result.recommendations,
                completed_at=negotiation_session.result.completed_at,
            )
            if negotiation_session.result
            else None
        ),
        messages=[
            MessageResponse(
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        negotiation_session, result = await complete_negotiation_session(
            db,
            session_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    messages = await get_messages(db, session_id)
    state = negotiation_session.state

    return SessionResponse(
        session_id=negotiation_session.id,
        status=negotiation_session.status,
        scenario_id=negotiation_session.scenario_id,
        state=(
            SessionStateResponse(
                metrics=state.metrics,
                turn_count=state.turn_count,
                detected_tactics=state.detected_tactics,
                coach_message=state.coach_message,
            )
            if state
            else None
        ),
        result=SessionResultResponse(
            final_score=result.final_score,
            outcome=result.outcome,
            final_metrics=result.final_metrics,
            strengths=result.strengths,
            mistakes=result.mistakes,
            recommendations=result.recommendations,
            completed_at=result.completed_at,
        ),
        messages=[
            MessageResponse(
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
