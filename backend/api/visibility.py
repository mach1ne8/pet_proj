from models import SessionState
from schemas import SessionStateResponse


EMOTIONAL_KEYS = {"irritation", "interest", "tension", "openness"}


def public_state(state: SessionState, difficulty: str, status: str) -> SessionStateResponse:
    if status == "completed" or difficulty == "analyst":
        metrics = state.metrics
    elif difficulty == "beginner":
        metrics = {key: value for key, value in state.metrics.items() if key in EMOTIONAL_KEYS}
    else:
        metrics = {}

    return SessionStateResponse(
        metrics=metrics,
        turn_count=state.turn_count,
        detected_tactics=state.detected_tactics,
        coach_message=state.coach_message if status == "completed" else "",
    )
