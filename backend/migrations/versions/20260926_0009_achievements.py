"""Persist achievements earned on completed negotiation sessions.

Revision ID: 20260926_0009
Revises: 20260926_0008
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260926_0009"
down_revision: Union[str, None] = "20260926_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_results",
        sa.Column("achievements", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("session_results", "achievements")
