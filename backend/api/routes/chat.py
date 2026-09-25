from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.visibility import public_state
from schemas import ChatRequest, ChatResponse
from services.negotiation import process_user_message


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        opponent_text, state, session, scenario = await process_user_message(
            db,
            request.session_id,
            request.message,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    return ChatResponse(
        message=opponent_text,
        state=public_state(state, session.difficulty, session.status),
        batna_revealed=session.batna_revealed,
        batna_text=scenario.batna if session.batna_revealed else None,
    )
