import uuid

from models import Scenario, SessionMetricEvent, SessionState
from services.llm.base import EvaluationResult


def clamp_metric(value: int) -> int:
    return max(0, min(100, value))


def create_initial_state(scenario: Scenario) -> SessionState:
    return SessionState(
        metrics={
            key: clamp_metric(int(value))
            for key, value in scenario.initial_metrics.items()
        },
        turn_count=0,
        detected_tactics=[],
        coach_message="Начните с уточнения интересов и ограничений собеседника.",
    )


def apply_evaluation(
    state: SessionState,
    evaluation: EvaluationResult,
) -> dict[str, int]:
    deltas = {
        "trust": evaluation.trust_delta,
        "irritation": evaluation.irritation_delta,
        "interest": evaluation.interest_delta,
        "tension": evaluation.tension_delta,
        "openness": evaluation.openness_delta,
        "risk": evaluation.risk_delta,
    }
    state.metrics = {
        key: clamp_metric(
            int(state.metrics.get(key, 0)) + delta
        )
        for key, delta in deltas.items()
    }
    state.turn_count += 1
    state.detected_tactics = evaluation.detected_tactics
    state.coach_message = evaluation.coach_message
    return deltas


def create_metric_event(
    session_id: uuid.UUID,
    state: SessionState,
    deltas: dict[str, int],
) -> SessionMetricEvent:
    return SessionMetricEvent(
        session_id=session_id,
        turn_count=state.turn_count,
        metrics=dict(state.metrics),
        deltas=deltas,
        detected_tactics=list(state.detected_tactics),
        coach_message=state.coach_message,
    )
