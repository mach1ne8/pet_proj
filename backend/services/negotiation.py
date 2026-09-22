import uuid

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models import Message, NegotiationSession, Scenario, SessionResult
from repositories.scenarios import get_default_scenario, get_scenario
from repositories.sessions import get_messages, get_session
from repositories.state import get_session_state
from services.llm.base import ConversationMessage, NegotiationContext
from services.llm.factory import get_llm_provider
from services.state import (
    apply_evaluation,
    create_initial_state,
    create_metric_event,
)


async def create_negotiation_session(
    db: AsyncSession,
    scenario_id: uuid.UUID | None = None,
) -> tuple[NegotiationSession, Message]:
    scenario: Scenario | None
    if scenario_id is None:
        scenario = await get_default_scenario(db)
    else:
        scenario = await get_scenario(db, scenario_id)

    if scenario is None:
        raise LookupError("Scenario not found")

    negotiation_session = NegotiationSession()
    negotiation_session.scenario_id = scenario.id
    negotiation_session.state = create_initial_state(scenario)
    db.add(negotiation_session)
    await db.flush()
    db.add(
        create_metric_event(
            negotiation_session.id,
            negotiation_session.state,
            {},
        )
    )

    initial_message = Message(
        session_id=negotiation_session.id,
        role="assistant",
        content=scenario.opening_message,
    )
    db.add(initial_message)
    await db.commit()

    return negotiation_session, initial_message


async def process_user_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
) -> tuple[str, object]:
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise LookupError("Session not found")

    if negotiation_session.status != "active":
        raise ValueError("Session is not active")

    scenario = await get_scenario(db, negotiation_session.scenario_id)
    if scenario is None:
        raise LookupError("Scenario not found")

    user_message = Message(
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(user_message)
    await db.flush()

    history = await get_messages(db, session_id)
    context = NegotiationContext(
        system_prompt=scenario.system_prompt,
        character_name=scenario.character_name,
        character_role=scenario.character_role,
        hidden_goal=scenario.hidden_goal,
        constraints=scenario.constraints,
        batna=scenario.batna,
        user_goals=scenario.user_goals,
        transcript=[
            ConversationMessage(
                role=("assistant" if item.role == "assistant" else "user"),
                content=item.content,
            )
            for item in history
        ],
        latest_user_message=content,
    )

    provider = get_llm_provider()
    turn = await provider.generate_turn(context)
    evaluation = turn.evaluation
    state = await get_session_state(db, session_id)
    if state is None:
        state = create_initial_state(scenario)
        state.session_id = session_id
        db.add(state)
    deltas = apply_evaluation(state, evaluation)
    db.add(create_metric_event(session_id, state, deltas))

    opponent_message = Message(
        session_id=session_id,
        role="assistant",
        content=turn.opponent_reply,
    )
    db.add(opponent_message)
    await db.commit()

    return opponent_message.content, state


def build_session_result(state) -> SessionResult:
    metrics = {
        key: int(value)
        for key, value in state.metrics.items()
    }
    score = round(
        (
            metrics.get("trust", 0)
            + metrics.get("interest", 0)
            + metrics.get("openness", 0)
            + (100 - metrics.get("risk", 100))
        )
        / 4
    )
    score = max(0, min(100, score))

    if score >= 75:
        outcome = "strong"
    elif score >= 50:
        outcome = "acceptable"
    else:
        outcome = "weak"

    strengths: list[str] = []
    if metrics.get("trust", 0) >= 65:
        strengths.append("Вы поддерживали доверие в диалоге.")
    if metrics.get("interest", 0) >= 65:
        strengths.append("Вы сохраняли интерес к поиску решения.")
    if metrics.get("openness", 0) >= 65:
        strengths.append("Вы помогали собеседнику оставаться открытым.")
    if not strengths:
        strengths.append("Вы довели переговоры до формального завершения.")

    mistakes: list[str] = []
    if metrics.get("risk", 0) >= 50:
        mistakes.append("Риск срыва остался высоким.")
    if metrics.get("irritation", 0) >= 50:
        mistakes.append("Раздражение собеседника заметно выросло.")
    if not mistakes:
        mistakes.append("Критических ошибок по текущим метрикам не выявлено.")

    return SessionResult(
        final_score=score,
        outcome=outcome,
        final_metrics=metrics,
        strengths=strengths,
        mistakes=mistakes,
        recommendations=[
            state.coach_message,
            "Фиксируйте обмен уступками и проверяйте ограничения обеих сторон.",
        ],
        completed_at=datetime.now(timezone.utc),
    )


async def complete_negotiation_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> tuple[NegotiationSession, SessionResult]:
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise LookupError("Session not found")
    if negotiation_session.status != "active":
        raise ValueError("Session is not active")
    if negotiation_session.state is None:
        raise LookupError("Session state not found")

    result = build_session_result(negotiation_session.state)
    negotiation_session.status = "completed"
    negotiation_session.updated_at = datetime.now(timezone.utc)
    negotiation_session.finished_at = result.completed_at
    negotiation_session.final_score = result.final_score
    negotiation_session.result = result
    db.add(result)
    await db.commit()

    return negotiation_session, result
