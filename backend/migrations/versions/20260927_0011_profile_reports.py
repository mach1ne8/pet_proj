"""Store asynchronous skill analyses for the browser-bound profile.

Revision ID: 20260927_0011
Revises: 20260926_0010
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260927_0011"
down_revision: Union[str, None] = "20260926_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profile_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("session_ids", postgresql.JSONB(), nullable=False),
        sa.Column("analysis", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("profile_reports")
