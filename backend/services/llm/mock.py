from services.llm.base import (
    EvaluationResult,
    LLMProvider,
    NegotiationContext,
)


class MockLLMProvider(LLMProvider):
    """Deterministic provider used until a real inference endpoint is configured."""

    async def generate_opponent_reply(
        self,
        context: NegotiationContext,
    ) -> str:
        message = context.latest_user_message.lower()

        if "объём" in message or "объем" in message:
            return (
                "При увеличении объёма заказа мы можем обсуждать более "
                "выгодную цену. Какой объём вы готовы зафиксировать?"
            )

        if "срок" in message or "гарант" in message:
            return (
                "Надёжные сроки для нас возможны при понятном графике "
                "заказов. Предложите ваш план поставок."
            )

        return (
            "Понимаю вашу позицию. Но цена для нас остаётся ключевым "
            "фактором. Какие условия вы можете предложить?"
        )

    async def evaluate_user_message(
        self,
        context: NegotiationContext,
    ) -> EvaluationResult:
        message = context.latest_user_message.lower()
        tactics: list[str] = []
        trust_delta = 0
        interest_delta = 0
        irritation_delta = 0

        if "?" in message:
            tactics.append("open_question")
            interest_delta += 2

        if "компромисс" in message or "объём" in message or "объем" in message:
            tactics.append("tradeoff")
            trust_delta += 2
            irritation_delta -= 1

        if not tactics:
            tactics.append("position_statement")

        return EvaluationResult(
            trust_delta=trust_delta,
            irritation_delta=irritation_delta,
            interest_delta=interest_delta,
            tension_delta=-irritation_delta,
            openness_delta=interest_delta,
            risk_delta=-trust_delta,
            detected_tactics=tactics,
            coach_message=(
                "Попробуйте связать уступку с конкретным обменом: "
                "объёмом, сроком или гарантией."
            ),
        )
