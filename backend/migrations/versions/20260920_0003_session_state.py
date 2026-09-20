"""Add current negotiation state and metrics.

Revision ID: 20260920_0003
Revises: 20260920_0002
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260920_0003"
down_revision: Union[str, None] = "20260920_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_states",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column(
            "detected_tactics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("coach_message", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.execute(
        sa.text(
            "INSERT INTO session_states "
            "(session_id, metrics, turn_count, detected_tactics, "
            "coach_message, updated_at) "
            "SELECT ns.id, s.initial_metrics, 0, '[]'::jsonb, "
            "'Начните с уточнения интересов и ограничений собеседника.', "
            "NOW() "
            "FROM negotiation_sessions ns "
            "JOIN scenarios s ON s.id = ns.scenario_id"
        )
    )


def downgrade() -> None:
    op.drop_table("session_states")
