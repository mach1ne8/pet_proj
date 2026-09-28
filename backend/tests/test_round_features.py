import unittest
import uuid
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from api.visibility import public_state, qualitative_signal
from services.llm.base import ConversationMessage, NegotiationContext, ProfileRound
from services.llm.mock import MockLLMProvider
from services.llm.openai_compatible import OpenAICompatibleProvider
from services.negotiation import build_session_result, earned_achievements, messages_before_turn, normalize_tactics, select_coach_hint, should_reveal_batna, suggest_user_message
from services.state import initial_metrics_for
from schemas import CreateProfileReportRequest


INITIAL = {
    "trust": 65, "interest": 78, "openness": 64,
    "risk": 26, "irritation": 35, "tension": 42,
}


class RoundFeaturesTest(unittest.TestCase):
    def test_profile_report_requires_bounded_session_list(self):
        with self.assertRaises(ValidationError):
            CreateProfileReportRequest(session_ids=[])
        with self.assertRaises(ValidationError):
            CreateProfileReportRequest(session_ids=[uuid.uuid4() for _ in range(21)])

    def state(self):
        return SimpleNamespace(metrics=dict(INITIAL), turn_count=0, detected_tactics=[], coach_message="")

    def test_no_dialogue_scores_zero(self):
        result = build_session_result(self.state(), INITIAL, [], 0)
        self.assertEqual(result.final_score, 0)
        self.assertEqual(result.outcome, "unplayed")
        self.assertEqual(result.achievements, [])
        self.assertTrue(all(value == 0 for value in result.skills.values()))

    def test_achievements_need_completed_meaningful_dialogue(self):
        self.assertEqual(earned_achievements([], INITIAL, INITIAL, 0, False), [])
        self.assertEqual(
            earned_achievements(["Здравствуйте"], INITIAL, INITIAL, 0, False),
            ["first_round"],
        )

    def test_all_five_achievements_have_distinct_conditions(self):
        final = {**INITIAL, "trust": INITIAL["trust"] + 10, "risk": INITIAL["risk"] - 5}
        messages = ["Какие условия важны?", "Что будет без соглашения?", "Какой объём нужен?"]
        self.assertEqual(
            earned_achievements(messages, INITIAL, final, 0, True),
            ["first_round", "curious_mind", "batna_scout", "independent", "trust_builder"],
        )
        self.assertNotIn("independent", earned_achievements(messages, INITIAL, final, 1, True))

    def test_hint_reduces_score(self):
        state = self.state()
        state.turn_count = 1
        state.detected_tactics = ["open_question"]
        history = [SimpleNamespace(role="user", content="Какие условия для вас важны?")]
        without_hint = build_session_result(state, INITIAL, history, 0)
        with_hint = build_session_result(state, INITIAL, history, 1)
        self.assertEqual(without_hint.final_score - with_hint.final_score, 8)

    def test_batna_requires_question_about_alternatives(self):
        self.assertTrue(should_reveal_batna("Какие у вас альтернативы, если не договоримся?"))
        self.assertFalse(should_reveal_batna("У нас есть альтернативы."))

    def test_tactics_are_normalized(self):
        self.assertEqual(
            normalize_tactics(["объём как рычаг для снижения цены"], "Какие объёмы возможны?"),
            ["tradeoff", "open_question"],
        )

    def test_metrics_are_filtered_by_difficulty(self):
        state = self.state()
        self.assertEqual(set(public_state(state, "beginner", "active").metrics), set(INITIAL))
        self.assertEqual(set(public_state(state, "analyst", "active").metrics), {"trust", "interest", "risk"})
        self.assertEqual(public_state(state, "advanced", "active").metrics, {})
        self.assertEqual(public_state(state, "expert", "active").metrics, {})
        self.assertEqual(len(public_state(state, "expert", "completed").metrics), 6)

    def test_qualitative_signal_is_only_visible_to_advanced_after_a_turn(self):
        state = self.state()
        state.detected_tactics = ["open_question"]
        self.assertIsNone(public_state(state, "advanced", "active", {"interest": 4}).signal)
        state.turn_count = 1
        advanced = public_state(state, "advanced", "active", {"interest": 4})
        self.assertEqual(advanced.signal, "Собеседник проявляет больше интереса.")
        self.assertEqual(advanced.metrics, {})
        self.assertIsNone(public_state(state, "analyst", "active", {"interest": 4}).signal)
        self.assertIsNone(public_state(state, "expert", "active", {"interest": 4}).signal)
        self.assertEqual(public_state(state, "expert", "active").detected_tactics, [])
        self.assertEqual(public_state(state, "expert", "completed").detected_tactics, ["open_question"])

    def test_qualitative_signal_describes_a_change_not_the_opponent_text(self):
        self.assertEqual(qualitative_signal({"risk": 4}), "Разговор стал более хрупким.")
        self.assertEqual(qualitative_signal({"trust": 3}), "Контакт с собеседником укрепился.")
        self.assertEqual(qualitative_signal({"interest": 0}), "Пока заметного сдвига в разговоре нет.")

    def test_initial_metrics_follow_difficulty(self):
        scenario = SimpleNamespace(initial_metrics=INITIAL)
        beginner = initial_metrics_for(scenario, "beginner")
        analyst = initial_metrics_for(scenario, "analyst")
        expert = initial_metrics_for(scenario, "expert")
        self.assertGreater(beginner["trust"], analyst["trust"])
        self.assertGreater(analyst["trust"], expert["trust"])
        self.assertLess(beginner["risk"], analyst["risk"])
        self.assertLess(analyst["risk"], expert["risk"])

    def test_rewind_keeps_only_turns_before_selected_reply(self):
        history = [
            SimpleNamespace(role="assistant", content="Старт"),
            SimpleNamespace(role="user", content="Первый ход"),
            SimpleNamespace(role="assistant", content="Ответ"),
            SimpleNamespace(role="user", content="Второй ход"),
            SimpleNamespace(role="assistant", content="Другой ответ"),
        ]
        self.assertEqual([item.content for item in messages_before_turn(history, 2)], ["Старт", "Первый ход", "Ответ"])
        self.assertEqual([item.content for item in messages_before_turn(history, 1)], ["Старт"])
        with self.assertRaises(ValueError):
            messages_before_turn(history, 3)

    def test_sos_has_three_different_messages_without_new_turn(self):
        hints = [select_coach_hint("Начните с открытого вопроса.", "Цена для нас важна.", index, False) for index in range(3)]
        self.assertEqual(len(set(hints)), 3)

    def test_fallback_key_moment_does_not_cut_word(self):
        state = self.state()
        state.turn_count = 1
        long_message = "Готовы подписать контракт на объёмы, которые вы укажете, при этом срок действия не менее 12 месяцев. " * 3
        result = build_session_result(state, INITIAL, [SimpleNamespace(role="user", content=long_message)], 0)
        self.assertTrue(result.key_moments[0].endswith("…"))
        self.assertFalse(result.key_moments[0].endswith("Провери"))


class ScenarioProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_profile_mock_uses_aggregate_skills(self):
        rounds = [
            ProfileRound(score=70, skills={"questions": 80, "empathy": 45, "argumentation": 50, "flexibility": 60, "self_control": 55}, strengths=["Вопросы"], mistakes=["Не уточнили интерес"], recommendations=[]),
            ProfileRound(score=60, skills={"questions": 70, "empathy": 55, "argumentation": 60, "flexibility": 50, "self_control": 45}, strengths=["Вопросы"], mistakes=["Не уточнили интерес"], recommendations=[]),
        ]
        analysis = await MockLLMProvider().analyze_profile(rounds)
        self.assertIn("2 завершённым", analysis.summary)
        self.assertIn("Вопросы", analysis.strengths[0])
        self.assertIn("Эмпатия", analysis.growth_areas[0])

    def context(self, role: str) -> NegotiationContext:
        return NegotiationContext(
            system_prompt="Ролевая ситуация",
            character_name="Собеседник",
            character_role=role,
            hidden_goal="Скрытая цель",
            constraints="Ограничение",
            batna="Альтернатива",
            user_goals=["Договориться об условиях"],
            transcript=[ConversationMessage(role="assistant", content="Обсудим условия.")],
            latest_user_message="Какие результаты важны?",
        )

    async def test_suggestion_uses_selected_scenario(self):
        provider = OpenAICompatibleProvider()
        provider._complete = AsyncMock(return_value="Какие результаты помогут принять решение?")
        await provider.suggest_user_message(self.context("Руководитель команды"), "open_question")
        prompt = provider._complete.await_args.args[0][0]["content"]
        self.assertIn("Руководитель команды", prompt)
        self.assertIn("Договориться об условиях", prompt)
        self.assertNotIn("закупщику", prompt)

    async def test_turn_retries_invalid_model_json(self):
        provider = OpenAICompatibleProvider()
        provider._complete = AsyncMock(side_effect=[
            '{"opponent_reply":',
            json.dumps({
                "opponent_reply": "Обсудим объём заказа.",
                "evaluation": {
                    "trust_delta": 1,
                    "irritation_delta": 0,
                    "interest_delta": 2,
                    "tension_delta": 0,
                    "openness_delta": 1,
                    "risk_delta": 0,
                    "detected_tactics": ["open_question"],
                    "coach_message": "Уточните условия.",
                },
            }, ensure_ascii=False),
        ])

        turn = await provider.generate_turn(self.context("Руководитель команды"))

        self.assertEqual(turn.opponent_reply, "Обсудим объём заказа.")
        self.assertEqual(provider._complete.await_count, 2)
        self.assertEqual(provider._complete.await_args.kwargs["max_tokens"], 320)

    async def test_mock_replies_match_character_role(self):
        provider = MockLLMProvider()
        salary = await provider.generate_opponent_reply(self.context("Руководитель команды"))
        deadline = await provider.generate_opponent_reply(self.context("Руководитель проекта со стороны клиента"))
        self.assertIn("достижения", salary)
        self.assertIn("запуска", deadline)

    async def test_quick_actions_are_not_available_on_higher_difficulties(self):
        for difficulty in ("advanced", "expert"):
            session = SimpleNamespace(status="active", expires_at=None, difficulty=difficulty)
            with patch("services.negotiation.get_session", new=AsyncMock(return_value=session)):
                with self.assertRaisesRegex(ValueError, "Quick actions"):
                    await suggest_user_message(AsyncMock(), uuid.uuid4(), "open_question")


if __name__ == "__main__":
    unittest.main()
