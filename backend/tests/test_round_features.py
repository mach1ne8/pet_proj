import unittest
from types import SimpleNamespace

from api.visibility import public_state
from services.negotiation import build_session_result, messages_before_turn, normalize_tactics, select_coach_hint, should_reveal_batna
from services.state import initial_metrics_for


INITIAL = {
    "trust": 65, "interest": 78, "openness": 64,
    "risk": 26, "irritation": 35, "tension": 42,
}


class RoundFeaturesTest(unittest.TestCase):
    def state(self):
        return SimpleNamespace(metrics=dict(INITIAL), turn_count=0, detected_tactics=[], coach_message="")

    def test_no_dialogue_scores_zero(self):
        result = build_session_result(self.state(), INITIAL, [], 0)
        self.assertEqual(result.final_score, 0)
        self.assertEqual(result.outcome, "unplayed")
        self.assertTrue(all(value == 0 for value in result.skills.values()))

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
        self.assertEqual(set(public_state(state, "beginner", "active").metrics), {"irritation", "interest", "tension", "openness"})
        self.assertEqual(len(public_state(state, "analyst", "active").metrics), 6)
        self.assertEqual(public_state(state, "expert", "active").metrics, {})
        self.assertEqual(len(public_state(state, "expert", "completed").metrics), 6)

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


if __name__ == "__main__":
    unittest.main()
