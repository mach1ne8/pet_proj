"""Persist round settings, timer, hints, notes and profile analysis.

Revision ID: 20260925_0005
Revises: 20260920_0004
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260925_0005"
down_revision: Union[str, None] = "20260920_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("negotiation_sessions", sa.Column("difficulty", sa.String(16), server_default="analyst", nullable=False))
    op.add_column("negotiation_sessions", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("negotiation_sessions", sa.Column("hints_used", sa.Integer(), server_default="0", nullable=False))
    op.add_column("negotiation_sessions", sa.Column("batna_revealed", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("negotiation_sessions", sa.Column("notes", sa.Text(), server_default="", nullable=False))
    op.add_column("session_results", sa.Column("key_moments", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("session_results", sa.Column("skills", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column("session_results", "skills")
    op.drop_column("session_results", "key_moments")
    op.drop_column("negotiation_sessions", "notes")
    op.drop_column("negotiation_sessions", "batna_revealed")
    op.drop_column("negotiation_sessions", "hints_used")
    op.drop_column("negotiation_sessions", "expires_at")
    op.drop_column("negotiation_sessions", "difficulty")
