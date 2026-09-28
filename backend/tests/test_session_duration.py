import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from schemas import CreateSessionRequest
from services.negotiation import create_negotiation_session, expire_if_needed, fork_negotiation_session


INITIAL_METRICS = {
    "trust": 60, "interest": 65, "openness": 55,
    "risk": 30, "irritation": 30, "tension": 40,
}


class SessionDurationSchemaTest(unittest.TestCase):
    def test_default_and_allowed_durations(self):
        self.assertEqual(CreateSessionRequest().duration_minutes, 10)
        for minutes in (10, 15, 20, 30, 45, 60):
            self.assertEqual(CreateSessionRequest(duration_minutes=minutes).duration_minutes, minutes)

    def test_invalid_durations_are_rejected(self):
        for minutes in (0, 9, 61, 10.5, "30", None):
            with self.subTest(minutes=minutes), self.assertRaises(ValidationError):
                CreateSessionRequest(duration_minutes=minutes)


class SessionDurationServiceTest(unittest.IsolatedAsyncioTestCase):
    def database(self):
        return SimpleNamespace(add=MagicMock(), add_all=MagicMock(), flush=AsyncMock(), commit=AsyncMock(), execute=AsyncMock())

    async def test_creation_sets_selected_duration_and_server_deadline(self):
        scenario = SimpleNamespace(id=uuid.uuid4(), initial_metrics=INITIAL_METRICS, opening_message="Обсудим условия.")
        now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
        for minutes in (10, 30, 60):
            with self.subTest(minutes=minutes):
                db = self.database()
                with patch("services.negotiation.get_scenario", new=AsyncMock(return_value=scenario)), patch("services.negotiation.datetime") as clock:
                    clock.now.return_value = now
                    session, message = await create_negotiation_session(db, scenario.id, "beginner", minutes)
                self.assertEqual(session.duration_minutes, minutes)
                self.assertEqual(session.expires_at, now + timedelta(minutes=minutes))
                self.assertEqual(message.content, scenario.opening_message)
                db.commit.assert_awaited_once()

    async def test_invalid_duration_does_not_touch_database(self):
        db = self.database()
        with self.assertRaises(ValueError):
            await create_negotiation_session(db, duration_minutes=61)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_expiration_uses_server_deadline(self):
        now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
        db = self.database()
        session = SimpleNamespace(id=uuid.uuid4(), status="active", expires_at=now + timedelta(minutes=60))
        with patch("services.negotiation.datetime") as clock, patch("services.negotiation.complete_negotiation_session", new=AsyncMock()) as complete:
            clock.now.return_value = now + timedelta(minutes=10)
            self.assertFalse(await expire_if_needed(db, session))
            complete.assert_not_awaited()
            clock.now.return_value = session.expires_at
            self.assertTrue(await expire_if_needed(db, session))
            complete.assert_awaited_once_with(db, session.id)

    async def test_rewind_preserves_duration_and_deadline(self):
        deadline = datetime.now(timezone.utc) + timedelta(minutes=50)
        parent = SimpleNamespace(
            id=uuid.uuid4(), scenario_id=uuid.uuid4(), status="active", difficulty="analyst",
            duration_minutes=60, expires_at=deadline, hints_used=1, hint_history=["Подсказка"], notes="Заметка",
        )
        history = [
            SimpleNamespace(role="assistant", content="Начало", created_at=deadline - timedelta(minutes=60)),
            SimpleNamespace(role="user", content="Мой ход", created_at=deadline - timedelta(minutes=59)),
        ]
        checkpoint = SimpleNamespace(
            turn_count=0, metrics=INITIAL_METRICS, deltas={}, detected_tactics=[], coach_message="",
            created_at=history[0].created_at,
        )
        db = self.database()
        events = MagicMock()
        events.scalars.return_value.all.return_value = [checkpoint]
        db.execute.return_value = events
        with patch("services.negotiation.get_session", new=AsyncMock(return_value=parent)), patch("services.negotiation.expire_if_needed", new=AsyncMock(return_value=False)), patch("services.negotiation.get_messages", new=AsyncMock(return_value=history)):
            branch, retained = await fork_negotiation_session(db, parent.id, 1)
        self.assertEqual(branch.duration_minutes, 60)
        self.assertEqual(branch.expires_at, deadline)
        self.assertEqual(len(retained), 1)
        self.assertEqual(branch.hints_used, 1)


if __name__ == "__main__":
    unittest.main()
