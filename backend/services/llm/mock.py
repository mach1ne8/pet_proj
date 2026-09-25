from textwrap import shorten

from services.llm.base import (
    ConversationMessage,
    EvaluationResult,
    LLMProvider,
    NegotiationContext,
    RoundSummary,
    TurnResult,
)


class MockLLMProvider(LLMProvider):
    """Deterministic provider used until a real inference endpoint is configured."""

    async def suggest_user_message(self, context: NegotiationContext, tactic: str) -> str:
        topic = "цене" if any("цен" in item.content.lower() for item in context.transcript[-3:]) else "условиях поставки"
        suggestions = {
            "open_question": f"Какие условия по {topic} для вас наиболее важны и почему?",
            "interests": f"Что для вас стоит за позицией по {topic}: сроки, объём или предсказуемость?",
            "facts": "Если мы зафиксируем объём и график заказов, сможем ли обсудить более выгодную цену?",
            "compromise": "Давайте зафиксируем объём на квартал в обмен на поэтапное снижение цены.",
        }
        return suggestions[tactic]

    async def summarize_round(self, transcript: list[ConversationMessage], score: int) -> RoundSummary:
        user_messages = [item.content for item in transcript if item.role == "user"]
        if not user_messages:
            return RoundSummary(strengths=[], mistakes=[], key_moments=[], recommendations=[])
        return RoundSummary(
            strengths=["Вы поддержали разговор и обозначили свою позицию."],
            mistakes=["Стоило яснее уточнить ограничения другой стороны."],
            key_moments=[f"Ваш первый ход: {shorten(user_messages[0], width=205, placeholder='…')}"],
            recommendations=["Задайте открытый вопрос об интересах и предложите обмен уступками."],
        )

    async def generate_turn(
        self,
        context: NegotiationContext,
    ) -> TurnResult:
        return TurnResult(
            opponent_reply=await self.generate_opponent_reply(context),
            evaluation=await self.evaluate_user_message(context),
        )

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
