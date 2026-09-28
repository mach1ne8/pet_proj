import unittest

from services.llm.base import NegotiationContext
from services.llm.mock import MockLLMProvider


class NewScenarioMockTest(unittest.IsolatedAsyncioTestCase):
    def context(self, role: str, message: str) -> NegotiationContext:
        return NegotiationContext(
            system_prompt="Ролевая ситуация", character_name="Собеседник", character_role=role,
            hidden_goal="Скрытая цель", constraints="Ограничения", batna="Альтернатива",
            user_goals=["Договориться"], transcript=[], latest_user_message=message,
        )

    async def test_office_lease_reply_matches_scenario(self):
        reply = await MockLLMProvider().generate_opponent_reply(self.context("Собственник офисного помещения", "Можем разделить депозит?"))
        self.assertIn("Депозит", reply)
        self.assertIn("аренды", reply)

    async def test_team_conflict_reply_matches_scenario(self):
        reply = await MockLLMProvider().generate_opponent_reply(self.context("Коллега — ведущий специалист команды", "Понимаю вашу нагрузку."))
        self.assertIn("задачи", reply)
        self.assertIn("нагрузку", reply)


if __name__ == "__main__":
    unittest.main()
