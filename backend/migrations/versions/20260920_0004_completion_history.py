"""Add metric history and session completion results.

Revision ID: 20260920_0004
Revises: 20260920_0003
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260920_0004"
down_revision: Union[str, None] = "20260920_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "negotiation_sessions",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "negotiation_sessions",
        sa.Column("final_score", sa.Integer(), nullable=True),
    )

    op.create_table(
        "session_metric_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deltas", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "detected_tactics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("coach_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_metric_events_session_id",
        "session_metric_events",
        ["session_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            "INSERT INTO session_metric_events "
            "(id, session_id, turn_count, metrics, deltas, "
            "detected_tactics, coach_message, created_at) "
            "SELECT gen_random_uuid(), session_id, turn_count, metrics, "
            "'{}'::jsonb, detected_tactics, coach_message, updated_at "
            "FROM session_states"
        )
    )

    op.create_table(
        "session_results",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("final_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mistakes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("session_results")
    op.drop_index(
        "ix_session_metric_events_session_id",
        table_name="session_metric_events",
    )
    op.drop_table("session_metric_events")
    op.drop_column("negotiation_sessions", "final_score")
    op.drop_column("negotiation_sessions", "finished_at")
