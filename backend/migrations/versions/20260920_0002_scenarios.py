"""Add negotiation scenarios and link sessions to a scenario.

Revision ID: 20260920_0002
Revises: 20260920_0001
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260920_0002"
down_revision: Union[str, None] = "20260920_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SCENARIO_ID = "11111111-1111-4111-8111-111111111111"


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("character_name", sa.String(length=255), nullable=False),
        sa.Column("character_role", sa.String(length=255), nullable=False),
        sa.Column("opening_message", sa.Text(), nullable=False),
        sa.Column("hidden_goal", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False),
        sa.Column("batna", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("user_goals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("initial_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("completion_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

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
                "id": DEFAULT_SCENARIO_ID,
                "slug": "supplier-procurement",
                "name": "Закупки с поставщиком",
                "description": (
                    "Переговоры о цене и условиях долгосрочной поставки."
                ),
                "character_name": "Алексей Воронцов",
                "character_role": "Коммерческий директор поставщика",
                "opening_message": (
                    "Нам нужно снизить цену минимум на 20%. "
                    "Иначе мы будем рассматривать другого поставщика."
                ),
                "hidden_goal": (
                    "Сохранить маржинальность не ниже 12% и заключить "
                    "годовой контракт."
                ),
                "constraints": (
                    "Нельзя снижать цену более чем на 20% без увеличения "
                    "объёма заказа или срока контракта."
                ),
                "batna": "Перейти к резервному поставщику с меньшей гибкостью.",
                "difficulty": "medium",
                "user_goals": [
                    "Снизить итоговую цену",
                    "Сохранить качество поставок",
                    "Зафиксировать надёжные сроки",
                ],
                "system_prompt": (
                    "Ты играешь роль коммерческого директора поставщика. "
                    "Сохраняй деловой тон, учитывай скрытые ограничения "
                    "и меняй готовность к уступкам по ходу переговоров."
                ),
                "initial_metrics": {
                    "trust": 65,
                    "irritation": 35,
                    "interest": 78,
                    "tension": 42,
                    "openness": 64,
                    "risk": 28,
                },
                "completion_rules": {
                    "max_turns": 12,
                    "allow_manual_finish": True,
                },
            }
        ],
    )

    op.add_column(
        "negotiation_sessions",
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE negotiation_sessions "
            "SET scenario_id = CAST(:scenario_id AS UUID) "
            "WHERE scenario_id IS NULL"
        ).bindparams(scenario_id=DEFAULT_SCENARIO_ID)
    )
    op.create_foreign_key(
        "fk_negotiation_sessions_scenario_id_scenarios",
        "negotiation_sessions",
        "scenarios",
        ["scenario_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column(
        "negotiation_sessions",
        "scenario_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "negotiation_sessions",
        "scenario_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_constraint(
        "fk_negotiation_sessions_scenario_id_scenarios",
        "negotiation_sessions",
        type_="foreignkey",
    )
    op.drop_column("negotiation_sessions", "scenario_id")
    op.drop_table("scenarios")
