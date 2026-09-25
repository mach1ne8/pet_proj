import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.visibility import public_state
from repositories.scenarios import get_scenario
from repositories.sessions import get_messages, get_session
from schemas import (
    CreateSessionRequest,
    ForkSessionRequest,
    HintResponse,
    MessageResponse,
    NotesRequest,
    SessionResponse,
    SessionResultResponse,
    SuggestionRequest,
    SuggestionResponse,
)
from services.negotiation import (
    complete_negotiation_session,
    create_negotiation_session,
    expire_if_needed,
    fork_negotiation_session,
    get_coach_hint,
    refine_session_summary,
    suggest_user_message,
)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


async def serialize_session(db: AsyncSession, session, messages) -> SessionResponse:
    scenario = await get_scenario(db, session.scenario_id) if session.batna_revealed else None
    state = session.state
    result = session.result
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        scenario_id=session.scenario_id,
        difficulty=session.difficulty,
        expires_at=session.expires_at,
        hints_used=session.hints_used,
        hint_history=session.hint_history,
        batna_revealed=session.batna_revealed,
        batna_text=scenario.batna if scenario else None,
        notes=session.notes,
        parent_session_id=session.parent_session_id,
        fork_from_turn=session.fork_from_turn,
        state=public_state(state, session.difficulty, session.status) if state else None,
        result=SessionResultResponse(
            final_score=result.final_score,
            outcome=result.outcome,
            final_metrics=result.final_metrics,
            strengths=result.strengths,
            mistakes=result.mistakes,
            recommendations=result.recommendations,
            key_moments=result.key_moments,
            skills=result.skills,
            analysis_status=result.analysis_status,
            completed_at=result.completed_at,
        ) if result else None,
        messages=[MessageResponse(role=item.role, content=item.content, created_at=item.created_at) for item in messages],
    )


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
                request.difficulty if request else "analyst",
            )
        )
    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    created = await get_session(db, negotiation_session.id)
    return await serialize_session(db, created, [initial_message])


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    await expire_if_needed(db, negotiation_session)
    if negotiation_session.result and negotiation_session.result.analysis_status == "pending":
        background_tasks.add_task(refine_session_summary, session_id)

    messages = await get_messages(db, session_id)
    return await serialize_session(db, negotiation_session, messages)


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        negotiation_session, _result = await complete_negotiation_session(
            db,
            session_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    messages = await get_messages(db, session_id)
    if negotiation_session.result and negotiation_session.result.analysis_status == "pending":
        background_tasks.add_task(refine_session_summary, session_id)
    return await serialize_session(db, negotiation_session, messages)


@router.post("/{session_id}/fork", response_model=SessionResponse)
async def fork_session(session_id: uuid.UUID, request: ForkSessionRequest, db: AsyncSession = Depends(get_db)):
    try:
        branch, messages = await fork_negotiation_session(db, session_id, request.turn_count, request.notes)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    created = await get_session(db, branch.id)
    return await serialize_session(db, created, messages)


@router.patch("/{session_id}/notes")
async def update_notes(session_id: uuid.UUID, request: NotesRequest, db: AsyncSession = Depends(get_db)):
    session = await get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.notes = request.notes
    await db.commit()
    return {"notes": session.notes}


@router.post("/{session_id}/hint", response_model=HintResponse)
async def request_hint(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        message, hints_used, history = await get_coach_hint(db, session_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return HintResponse(message=message, hints_used=hints_used, history=history)


@router.post("/{session_id}/suggest", response_model=SuggestionResponse)
async def suggest_message(session_id: uuid.UUID, request: SuggestionRequest, db: AsyncSession = Depends(get_db)):
    try:
        text = await suggest_user_message(db, session_id, request.tactic)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return SuggestionResponse(message=text)
