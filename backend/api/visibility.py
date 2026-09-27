from collections.abc import Mapping

from models import SessionState
from schemas import SessionStateResponse


EMOTIONAL_KEYS = {"irritation", "tension", "openness"}
NEGOTIATION_KEYS = {"trust", "interest", "risk"}


def qualitative_signal(deltas: Mapping[str, int]) -> str:
    """One deliberately coarse observation, never the private evaluator text."""
    observations = [
        ("risk", "Разговор стал более хрупким.", "Напряжение вокруг соглашения ослабло."),
        ("irritation", "Собеседник реагирует резче.", "Тон собеседника стал спокойнее."),
        ("tension", "В разговоре прибавилось напряжения.", "Напряжение в разговоре снизилось."),
        ("trust", "Контакт с собеседником укрепился.", "Собеседник стал осторожнее в оценке ваших слов."),
        ("interest", "Собеседник проявляет больше интереса.", "Интерес к обсуждению ослаб."),
        ("openness", "Собеседник стал открытее к обсуждению.", "Собеседник отвечает более закрыто."),
    ]
    key, positive, negative = max(observations, key=lambda item: abs(int(deltas.get(item[0], 0))))
    change = int(deltas.get(key, 0))
    if abs(change) < 2:
        return "Пока заметного сдвига в разговоре нет."
    # Risk, irritation and tension increasing are negative; trust, interest and openness increasing are positive.
    return positive if change > 0 else negative


def public_state(
    state: SessionState,
    difficulty: str,
    status: str,
    last_deltas: Mapping[str, int] | None = None,
) -> SessionStateResponse:
    if status == "completed":
        metrics = state.metrics
    elif difficulty == "beginner":
        metrics = {key: value for key, value in state.metrics.items() if key in EMOTIONAL_KEYS | NEGOTIATION_KEYS}
    elif difficulty == "analyst":
        metrics = {key: value for key, value in state.metrics.items() if key in NEGOTIATION_KEYS}
    else:
        metrics = {}

    return SessionStateResponse(
        metrics=metrics,
        turn_count=state.turn_count,
        detected_tactics=[] if difficulty == "expert" and status == "active" else state.detected_tactics,
        coach_message=state.coach_message if status == "completed" else "",
        signal=qualitative_signal(last_deltas) if difficulty == "advanced" and status == "active" and state.turn_count and last_deltas is not None else None,
    )
