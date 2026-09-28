from textwrap import shorten

from services.llm.base import (
    ConversationMessage,
    EvaluationResult,
    LLMProvider,
    NegotiationContext,
    RoundSummary,
    ProfileRound,
    ProfileAnalysis,
    TurnResult,
)


class MockLLMProvider(LLMProvider):
    """Deterministic provider used until a real inference endpoint is configured."""

    async def analyze_profile(self, rounds: list[ProfileRound]) -> ProfileAnalysis:
        labels = {
            "questions": "вопросы", "empathy": "эмпатия", "argumentation": "аргументация",
            "flexibility": "гибкость", "self_control": "самоконтроль",
        }
        averages = {
            key: round(sum(item.skills.get(key, 0) for item in rounds) / len(rounds))
            for key in labels
        }
        best = max(averages, key=averages.get)
        weakest = min(averages, key=averages.get)
        count_label = "одному завершённому раунду" if len(rounds) == 1 else f"{len(rounds)} завершённым раундам"
        return ProfileAnalysis(
            summary=f"По {count_label} сильнее всего проявляются {labels[best]}. Оценки ориентировочные: сравнивайте их вместе с конкретными репликами.",
            strengths=[f"{labels[best].capitalize()}: в среднем {averages[best]}/100 по завершённым раундам."],
            growth_areas=[f"{labels[weakest].capitalize()}: в среднем {averages[weakest]}/100; навык стоит тренировать чаще."],
            next_steps=["В следующем раунде задайте открытый вопрос об интересах собеседника и зафиксируйте его ответ."],
        )

    async def suggest_user_message(self, context: NegotiationContext, tactic: str) -> str:
        suggestions = {
            "open_question": "Какие условия для вас сейчас наиболее важны и почему?",
            "interests": "Что для вас стоит за этой позицией: сроки, ресурсы или предсказуемость?",
            "facts": "Давайте уточним факты и ограничения, прежде чем соглашаться на условия.",
            "compromise": "Если мы согласуем приоритеты и сроки, сможете ли вы пересмотреть свою позицию?",
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

        if "собственник офисного" in context.character_role.lower():
            if any(word in message for word in ("депозит", "каникул", "переезд")):
                return "Депозит можно разделить на два платежа. Какие обязательства по сроку аренды вы готовы предложить взамен?"
            return "Долгосрочный договор и предсказуемые платежи для меня важны. На какой срок вы готовы арендовать офис?"

        if "ведущий специалист" in context.character_role.lower():
            if any(word in message for word in ("нагруз", "приоритет", "понима")):
                return "Спасибо, что учитываете нагрузку. Какие задачи мы снимем или перенесём, прежде чем добавлять новые?"
            return "Мне важно понятное распределение работы, а не очередное обещание. Как вы предлагаете разделить задачи?"

        if "руководитель команды" in context.character_role.lower():
            if any(word in message for word in ("результат", "достиж", "вклад")):
                return "Результаты важны для решения. Какие конкретные достижения вы предлагаете взять за основу пересмотра?"
            if any(word in message for word in ("срок", "квартал", "бюджет")):
                return "В этом квартале бюджет ограничен. Давайте определим критерии и дату повторного обсуждения."
            return "Я готова обсудить ваш запрос. Что изменилось в вашей роли и какой пересмотр вы считаете обоснованным?"

        if "со стороны клиента" in context.character_role.lower():
            if any(word in message for word in ("объём", "объем", "функц", "приоритет")):
                return "Давайте выделим функции, без которых первый запуск невозможен. Что вы предлагаете перенести на следующий этап?"
            if any(word in message for word in ("бюджет", "ресурс", "команд")):
                return "Дополнительные ресурсы нужно обосновать. Как они повлияют на срок запуска и качество?"
            return "Срок запуска для нас критичен. Какие варианты по этапам вы видите без риска для ключевых функций?"

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
                "Попробуйте связать уступку с конкретным встречным условием "
                "и уточнить, что важно собеседнику."
            ),
        )
