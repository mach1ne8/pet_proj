import uuid
import logging
import asyncio
from textwrap import shorten

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal
from models import Message, NegotiationSession, Scenario, SessionMetricEvent, SessionResult, SessionState
from repositories.scenarios import get_default_scenario, get_scenario
from repositories.sessions import get_messages, get_session
from repositories.state import get_session_state
from services.llm.base import ConversationMessage, NegotiationContext
from services.llm.factory import get_llm_provider
from services.state import (
    apply_evaluation,
    create_initial_state,
    create_metric_event,
    initial_metrics_for,
)


logger = logging.getLogger(__name__)
ROUND_DURATION = timedelta(minutes=10)
_running_summaries: set[uuid.UUID] = set()
_summary_semaphore = asyncio.Semaphore(1)


def should_reveal_batna(content: str) -> bool:
    text = content.casefold()
    questions = ("?" in text or any(word in text for word in ("какая", "какие", "что будет", "есть ли", "кто ещё")))
    topics = ("альтернатив", "если не договор", "если мы не договор", "без соглашения", "другие поставщик", "другой поставщик", "запасной вариант", "батна", "batna")
    return questions and any(topic in text for topic in topics)


def normalize_tactics(raw: list[str], content: str) -> list[str]:
    known = {"open_question", "empathy", "position_statement", "fact_based_argument", "concession", "compromise", "tradeoff", "batna", "spin", "principled_negotiation"}
    mapped: list[str] = []
    for item in raw:
        text = item.casefold()
        if item in known:
            mapped.append(item)
        elif "альтернатив" in text or "batna" in text or "батна" in text:
            mapped.append("batna")
        elif "объём" in text or "объем" in text or "обмен" in text or "услови" in text:
            mapped.append("tradeoff")
        elif "эмпат" in text or "пониман" in text:
            mapped.append("empathy")
        elif "компромисс" in text:
            mapped.append("compromise")
        elif "факт" in text or "аргумент" in text:
            mapped.append("fact_based_argument")
        elif "вопрос" in text:
            mapped.append("open_question")
    if "?" in content:
        mapped.append("open_question")
    if should_reveal_batna(content):
        mapped.append("batna")
    return list(dict.fromkeys(mapped or ["position_statement"]))


def build_context(scenario: Scenario, history: list[Message], latest: str = "", difficulty: str = "analyst") -> NegotiationContext:
    return NegotiationContext(
        system_prompt=scenario.system_prompt,
        character_name=scenario.character_name,
        character_role=scenario.character_role,
        hidden_goal=scenario.hidden_goal,
        constraints=scenario.constraints,
        batna=scenario.batna,
        user_goals=scenario.user_goals,
        transcript=[ConversationMessage(role=item.role, content=item.content) for item in history],
        latest_user_message=latest,
        difficulty=difficulty,
    )


async def create_negotiation_session(
    db: AsyncSession,
    scenario_id: uuid.UUID | None = None,
    difficulty: str = "analyst",
) -> tuple[NegotiationSession, Message]:
    scenario: Scenario | None
    if scenario_id is None:
        scenario = await get_default_scenario(db)
    else:
        scenario = await get_scenario(db, scenario_id)

    if scenario is None:
        raise LookupError("Scenario not found")

    negotiation_session = NegotiationSession(
        difficulty=difficulty,
        expires_at=datetime.now(timezone.utc) + ROUND_DURATION,
    )
    negotiation_session.scenario_id = scenario.id
    negotiation_session.state = create_initial_state(scenario, difficulty)
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


def messages_before_turn(history: list[Message], target_turn: int) -> list[Message]:
    """Keep the opening and all completed turns before the selected user reply."""
    if target_turn < 1:
        raise ValueError("Turn number must be positive")
    retained: list[Message] = []
    user_turn = 0
    for item in history:
        if item.role == "user":
            user_turn += 1
            if user_turn == target_turn:
                return retained
        retained.append(item)
    raise ValueError("Selected user turn not found")


async def fork_negotiation_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    target_turn: int,
    notes: str | None = None,
) -> tuple[NegotiationSession, list[Message]]:
    parent = await get_session(db, session_id)
    if parent is None:
        raise LookupError("Session not found")
    if parent.status != "active" or await expire_if_needed(db, parent):
        raise ValueError("Only an active session can be rewound")
    if parent.expires_at is None:
        raise ValueError("Rewind is available for new timed sessions")

    history = await get_messages(db, session_id)
    retained = messages_before_turn(history, target_turn)
    checkpoint_turn = target_turn - 1
    events = list((await db.execute(
        select(SessionMetricEvent)
        .where(SessionMetricEvent.session_id == session_id, SessionMetricEvent.turn_count <= checkpoint_turn)
        .order_by(SessionMetricEvent.turn_count, SessionMetricEvent.created_at, SessionMetricEvent.id)
    )).scalars().all())
    checkpoint = next((item for item in reversed(events) if item.turn_count == checkpoint_turn), None)
    if checkpoint is None or not events or events[0].turn_count != 0:
        raise ValueError("Checkpoint for the selected turn is unavailable")

    branch = NegotiationSession(
        scenario_id=parent.scenario_id,
        difficulty=parent.difficulty,
        expires_at=parent.expires_at,
        hints_used=parent.hints_used,
        hint_history=list(parent.hint_history),
        batna_revealed=any(should_reveal_batna(item.content) for item in retained if item.role == "user"),
        notes=parent.notes if notes is None else notes,
        parent_session_id=parent.id,
        fork_from_turn=target_turn,
    )
    branch.state = SessionState(
        metrics=dict(checkpoint.metrics),
        turn_count=checkpoint.turn_count,
        detected_tactics=list(checkpoint.detected_tactics),
        coach_message=checkpoint.coach_message,
    )
    db.add(branch)
    await db.flush()

    copied_messages = [
        Message(session_id=branch.id, role=item.role, content=item.content, created_at=item.created_at)
        for item in retained
    ]
    db.add_all(copied_messages)
    db.add_all([
        SessionMetricEvent(
            session_id=branch.id,
            turn_count=item.turn_count,
            metrics=dict(item.metrics),
            deltas=dict(item.deltas),
            detected_tactics=list(item.detected_tactics),
            coach_message=item.coach_message,
            created_at=item.created_at,
        )
        for item in events
    ])
    await db.commit()
    return branch, copied_messages


async def process_user_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
) -> tuple[str, object, NegotiationSession, Scenario]:
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise LookupError("Session not found")

    if negotiation_session.status != "active":
        raise ValueError("Session is not active")

    if await expire_if_needed(db, negotiation_session):
        raise ValueError("Session time has expired")

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
    context = build_context(scenario, history, content, negotiation_session.difficulty)

    provider = get_llm_provider()
    turn = await provider.generate_turn(context)
    evaluation = turn.evaluation.model_copy(update={
        "detected_tactics": normalize_tactics(turn.evaluation.detected_tactics, content),
    })
    state = await get_session_state(db, session_id)
    if state is None:
        state = create_initial_state(scenario, negotiation_session.difficulty)
        state.session_id = session_id
        db.add(state)
    deltas = apply_evaluation(state, evaluation)
    if should_reveal_batna(content):
        negotiation_session.batna_revealed = True
    db.add(create_metric_event(session_id, state, deltas))

    opponent_message = Message(
        session_id=session_id,
        role="assistant",
        content=turn.opponent_reply,
    )
    db.add(opponent_message)
    await db.commit()

    return opponent_message.content, state, negotiation_session, scenario


def build_session_result(state, initial_metrics: dict[str, int], history: list[Message], hints_used: int) -> SessionResult:
    metrics = {key: int(value) for key, value in state.metrics.items()}
    user_messages = [item.content for item in history if item.role == "user"]
    turns = len(user_messages)
    tactics = set(state.detected_tactics)
    if turns:
        gains = [metrics.get(key, 0) - int(initial_metrics.get(key, 0)) for key in ("trust", "interest", "openness")]
        gains += [int(initial_metrics.get(key, 0)) - metrics.get(key, 0) for key in ("risk", "irritation", "tension")]
        impact = sum(gains) / len(gains)
        score = round(32 + min(turns, 8) * 4 + impact * 1.25 + min(len(tactics), 5) * 4 - hints_used * 8)
        score = max(0, min(100, score))
        questions = sum("?" in text for text in user_messages)
        empathy = sum(any(word in text.casefold() for word in ("понимаю", "важно для вас", "слышу вас")) for text in user_messages)
        arguments = sum(any(word in text.casefold() for word in ("если", "потому", "данные", "факт", "%")) for text in user_messages)
        trades = sum(any(word in text.casefold() for word in ("взамен", "компромисс", "обмен", "уступ")) for text in user_messages)
        skill_values = {
            "questions": 15 + questions * 17 + max(0, gains[1]) * 2,
            "empathy": 15 + empathy * 22 + max(0, gains[0]) * 2,
            "argumentation": 15 + arguments * 19 + max(0, gains[2]) * 2,
            "flexibility": 15 + trades * 22 + max(0, gains[3]) * 2,
            "self_control": 20 + min(turns, 6) * 5 + (gains[4] + gains[5]) * 2,
        }
        skills = {key: max(0, min(100, round(value))) for key, value in skill_values.items()}
        strengths = ["Вы вели содержательный диалог и проверяли условия собеседника."]
        mistakes = ["Уточняйте интересы второй стороны до предложения уступок."]
        key_moments = [f"Первый ход: {shorten(user_messages[0], width=205, placeholder='…')}"]
        recommendations = [state.coach_message or "Начните с открытого вопроса об интересах собеседника."]
    else:
        score = 0
        skills = {key: 0 for key in ("questions", "empathy", "argumentation", "flexibility", "self_control")}
        strengths = []
        mistakes = ["Вы не отправили ни одной реплики."]
        key_moments = []
        recommendations = ["Начните следующий раунд с открытого вопроса."]

    outcome = "unplayed" if not turns else "strong" if score >= 75 else "acceptable" if score >= 50 else "weak"
    return SessionResult(
        final_score=score,
        outcome=outcome,
        final_metrics=metrics,
        strengths=strengths,
        mistakes=mistakes,
        key_moments=key_moments,
        skills=skills,
        recommendations=recommendations,
        completed_at=datetime.now(timezone.utc),
    )


async def complete_negotiation_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> tuple[NegotiationSession, SessionResult]:
    negotiation_session = await get_session(db, session_id)

    if negotiation_session is None:
        raise LookupError("Session not found")
    if negotiation_session.status == "completed" and negotiation_session.result is not None:
        return negotiation_session, negotiation_session.result
    if negotiation_session.status != "active":
        raise ValueError("Session is not active")
    if negotiation_session.state is None:
        raise LookupError("Session state not found")

    scenario = await get_scenario(db, negotiation_session.scenario_id)
    if scenario is None:
        raise LookupError("Scenario not found")
    history = await get_messages(db, session_id)
    initial_event = (await db.execute(
        select(SessionMetricEvent)
        .where(SessionMetricEvent.session_id == session_id, SessionMetricEvent.turn_count == 0)
        .order_by(SessionMetricEvent.created_at, SessionMetricEvent.id)
        .limit(1)
    )).scalar_one_or_none()
    baseline = initial_event.metrics if initial_event else initial_metrics_for(scenario, negotiation_session.difficulty)
    result = build_session_result(negotiation_session.state, baseline, history, negotiation_session.hints_used)
    result.analysis_status = "pending" if negotiation_session.state.turn_count else "ready"
    negotiation_session.status = "completed"
    negotiation_session.updated_at = datetime.now(timezone.utc)
    negotiation_session.finished_at = result.completed_at
    negotiation_session.final_score = result.final_score
    negotiation_session.result = result
    db.add(result)
    await db.commit()

    return negotiation_session, result


async def refine_session_summary(session_id: uuid.UUID) -> None:
    """Enrich an already persisted result without delaying session completion."""
    if session_id in _running_summaries:
        return
    _running_summaries.add(session_id)
    try:
        async with SessionLocal() as db:
            session = await get_session(db, session_id)
            if session is None or session.result is None or session.result.analysis_status != "pending":
                return
            history = await get_messages(db, session_id)
            score = session.result.final_score

        try:
            async with _summary_semaphore:
                summary = await get_llm_provider().summarize_round(
                    [ConversationMessage(role=item.role, content=item.content) for item in history],
                    score,
                )
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            logger.warning("LLM summary unavailable for session %s (%s, HTTP %s); using metric summary", session_id, type(error).__name__, status)
            summary = None
        if summary is not None and not all((summary.strengths, summary.mistakes, summary.key_moments, summary.recommendations)):
            logger.warning("LLM summary incomplete for session %s; using metric summary", session_id)
            summary = None

        async with SessionLocal() as db:
            session = await get_session(db, session_id)
            if session is None or session.result is None or session.result.analysis_status != "pending":
                return
            if summary is not None:
                session.result.strengths = summary.strengths or session.result.strengths
                session.result.mistakes = summary.mistakes or session.result.mistakes
                session.result.key_moments = summary.key_moments or session.result.key_moments
                session.result.recommendations = summary.recommendations or session.result.recommendations
                session.result.analysis_status = "ready"
            else:
                session.result.analysis_status = "failed"
            await db.commit()
    finally:
        _running_summaries.discard(session_id)


async def expire_if_needed(db: AsyncSession, session: NegotiationSession) -> bool:
    if session.status == "active" and session.expires_at and datetime.now(timezone.utc) >= session.expires_at:
        await complete_negotiation_session(db, session.id)
        return True
    return False


def select_coach_hint(coach_message: str, opponent_text: str, hint_number: int, batna_revealed: bool) -> str:
    if hint_number == 0:
        return coach_message.strip() or "Начните с вопроса о том, какие условия для собеседника важнее цены."
    if hint_number == 1:
        if "срок" in opponent_text.casefold() or "постав" in opponent_text.casefold():
            return "Уточните, какой график поставок собеседник сможет гарантировать и что для этого нужно с вашей стороны."
        return "Спросите, какие объём или срок контракта позволят обсудить встречную уступку по цене."
    if not batna_revealed:
        return "Проверьте альтернативу: что собеседник сделает, если соглашения не будет? Затем предложите обмен, а не одностороннюю уступку."
    return "Сформулируйте конкретный обмен: что вы готовы дать и какое обязательство хотите получить взамен."


async def get_coach_hint(db: AsyncSession, session_id: uuid.UUID) -> tuple[str, int, list[str]]:
    session = await get_session(db, session_id)
    if session is None:
        raise LookupError("Session not found")
    if session.status != "active" or await expire_if_needed(db, session):
        raise ValueError("Session is not active")
    if session.difficulty not in {"beginner", "analyst"}:
        raise ValueError("SOS is available only for beginner and analyst")
    if session.hints_used >= 3:
        raise ValueError("SOS limit reached")
    history = await get_messages(db, session_id)
    latest_opponent = next((item.content for item in reversed(history) if item.role == "assistant"), "")
    hint = select_coach_hint(session.state.coach_message, latest_opponent, session.hints_used, session.batna_revealed)
    if hint in session.hint_history:
        hint = "Подведите итог услышанного и задайте один уточняющий вопрос, прежде чем переходить к уступкам."
    session.hints_used += 1
    session.hint_history = [*session.hint_history, hint]
    await db.commit()
    return hint, session.hints_used, session.hint_history


async def suggest_user_message(db: AsyncSession, session_id: uuid.UUID, tactic: str) -> str:
    session = await get_session(db, session_id)
    if session is None:
        raise LookupError("Session not found")
    if session.status != "active" or await expire_if_needed(db, session):
        raise ValueError("Session is not active")
    scenario = await get_scenario(db, session.scenario_id)
    if scenario is None:
        raise LookupError("Scenario not found")
    history = await get_messages(db, session_id)
    suggestion = await get_llm_provider().suggest_user_message(build_context(scenario, history, difficulty=session.difficulty), tactic)
    if not suggestion.strip():
        raise ValueError("No suggestion generated")
    return suggestion.strip()[:500]
