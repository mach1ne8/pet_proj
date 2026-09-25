"""Persist SOS history and asynchronous analysis status.

Revision ID: 20260926_0008
Revises: 20260926_0007
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260926_0008"
down_revision: Union[str, None] = "20260926_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "negotiation_sessions",
        sa.Column("hint_history", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column(
        "session_results",
        sa.Column("analysis_status", sa.String(16), server_default="ready", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("session_results", "analysis_status")
    op.drop_column("negotiation_sessions", "hint_history")
