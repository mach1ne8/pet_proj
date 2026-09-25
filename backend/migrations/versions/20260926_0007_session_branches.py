"""Track non-destructive branches of negotiation sessions.

Revision ID: 20260926_0007
Revises: 20260925_0006
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260926_0007"
down_revision: Union[str, None] = "20260925_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("negotiation_sessions", sa.Column("parent_session_id", sa.Uuid(), nullable=True))
    op.add_column("negotiation_sessions", sa.Column("fork_from_turn", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_negotiation_sessions_parent_session_id",
        "negotiation_sessions", "negotiation_sessions",
        ["parent_session_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_negotiation_sessions_parent_session_id", "negotiation_sessions", ["parent_session_id"])


def downgrade() -> None:
    op.drop_index("ix_negotiation_sessions_parent_session_id", table_name="negotiation_sessions")
    op.drop_constraint("fk_negotiation_sessions_parent_session_id", "negotiation_sessions", type_="foreignkey")
    op.drop_column("negotiation_sessions", "fork_from_turn")
    op.drop_column("negotiation_sessions", "parent_session_id")
