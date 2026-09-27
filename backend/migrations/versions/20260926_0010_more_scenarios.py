"""Add salary and project-deadline negotiation scenarios.

Revision ID: 20260926_0010
Revises: 20260926_0009
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260926_0010"
down_revision: Union[str, None] = "20260926_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SALARY_ID = "22222222-2222-4222-8222-222222222222"
DEADLINE_ID = "33333333-3333-4333-8333-333333333333"


def upgrade() -> None:
    scenarios = sa.table(
        "scenarios",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("character_name", sa.String()),
        sa.column("character_role", sa.String()),
        sa.column("opening_message", sa.Text()),
        sa.column("hidden_goal", sa.Text()),
        sa.column("constraints", sa.Text()),
        sa.column("batna", sa.Text()),
        sa.column("difficulty", sa.String()),
        sa.column("user_goals", postgresql.JSONB()),
        sa.column("system_prompt", sa.Text()),
        sa.column("initial_metrics", postgresql.JSONB()),
        sa.column("completion_rules", postgresql.JSONB()),
    )
    op.bulk_insert(
        scenarios,
        [
            {
                "id": SALARY_ID,
                "slug": "salary-review",
                "name": "Повышение зарплаты",
                "description": "Обсудите рост компенсации с руководителем на фоне ограниченного бюджета.",
                "character_name": "Марина Соколова",
                "character_role": "Руководитель команды",
                "opening_message": (
                    "Вы предложили пересмотреть зарплату. Я готова обсудить это, "
                    "но бюджет на этот квартал ограничен. На каких результатах "
                    "и ожиданиях основан ваш запрос?"
                ),
                "hidden_goal": (
                    "Сохранить ценного сотрудника и договориться о прозрачных "
                    "критериях роста, не выходя за рамки бюджета команды."
                ),
                "constraints": (
                    "Немедленное повышение возможно не более чем на 8%; "
                    "существенный пересмотр требует согласования в следующем квартале."
                ),
                "batna": (
                    "Сохранить текущие условия до следующего бюджетного цикла "
                    "и предложить план развития, рискуя потерять сотрудника."
                ),
                "difficulty": "medium",
                "user_goals": [
                    "Добиться справедливого пересмотра зарплаты",
                    "Договориться о сроках и критериях решения",
                    "Сохранить рабочие отношения с руководителем",
                ],
                "system_prompt": (
                    "Ты — Марина Соколова, руководитель команды. Собеседник — "
                    "сотрудник, который просит повысить зарплату. Реагируй на "
                    "конкретные результаты, рыночные аргументы и разумные "
                    "компромиссы. Не обещай согласование, которого у тебя нет. "
                    "Веди живой деловой диалог, задавай уточняющие вопросы."
                ),
                "initial_metrics": {
                    "trust": 62, "irritation": 28, "interest": 65,
                    "tension": 38, "openness": 60, "risk": 32,
                },
                "completion_rules": {"max_turns": 12, "allow_manual_finish": True},
            },
            {
                "id": DEADLINE_ID,
                "slug": "project-deadline",
                "name": "Сроки проекта с клиентом",
                "description": "Согласуйте реалистичный срок запуска и объём работ с требовательным клиентом.",
                "character_name": "Ирина Белова",
                "character_role": "Руководитель проекта со стороны клиента",
                "opening_message": (
                    "Нам нужен запуск на две недели раньше плана, при этом "
                    "объём работ и бюджет желательно оставить прежними. "
                    "Что вы можете предложить?"
                ),
                "hidden_goal": (
                    "Успеть показать работающую версию продукта к отраслевому "
                    "мероприятию, сохранив качество ключевых функций."
                ),
                "constraints": (
                    "Дополнительный бюджет не может превышать 15%; "
                    "допустим перенос второстепенных функций на следующий релиз."
                ),
                "batna": (
                    "Запустить урезанную демонстрационную версию силами внутренней "
                    "команды, приняв риск задержки и потери качества."
                ),
                "difficulty": "medium",
                "user_goals": [
                    "Не обещать невыполнимый срок для полного объёма работ",
                    "Согласовать приоритеты первого релиза",
                    "Сохранить доверие клиента и прозрачные условия проекта",
                ],
                "system_prompt": (
                    "Ты — Ирина Белова, руководитель проекта заказчика. "
                    "Собеседник — подрядчик, с которым ты согласовываешь "
                    "ускорение запуска. Настойчиво защищай сроки, но слушай "
                    "обоснованные предложения об этапах, приоритетах и ресурсах. "
                    "Не соглашайся на нереалистичные обещания без уточнений."
                ),
                "initial_metrics": {
                    "trust": 58, "irritation": 34, "interest": 72,
                    "tension": 48, "openness": 54, "risk": 38,
                },
                "completion_rules": {"max_turns": 12, "allow_manual_finish": True},
            },
        ],
    )


def downgrade() -> None:
    connection = op.get_bind()
    in_use = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM negotiation_sessions "
            "WHERE scenario_id IN (CAST(:salary_id AS UUID), CAST(:deadline_id AS UUID)))"
        ).bindparams(salary_id=SALARY_ID, deadline_id=DEADLINE_ID)
    ).scalar_one()
    if in_use:
        raise RuntimeError("Cannot remove scenarios with existing negotiation sessions")
    connection.execute(
        sa.text("DELETE FROM scenarios WHERE id IN (CAST(:salary_id AS UUID), CAST(:deadline_id AS UUID))").bindparams(
            salary_id=SALARY_ID, deadline_id=DEADLINE_ID
        )
    )
