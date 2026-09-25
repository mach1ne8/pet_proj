"""Correct the seeded supplier's opening and fallback option.

Revision ID: 20260925_0006
Revises: 20260925_0005
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_0006"
down_revision: Union[str, None] = "20260925_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_OPENING = "Нам нужно снизить цену минимум на 20%. Иначе мы будем рассматривать другого поставщика."
NEW_OPENING = "Вы просите снизить цену на 20%. Для нас это серьёзный шаг. Какие объёмы и срок контракта вы готовы предложить взамен?"
OLD_BATNA = "Перейти к резервному поставщику с меньшей гибкостью."
NEW_BATNA = "Продолжить продажи другим клиентам по текущей цене, но потерять объём вашего годового контракта."


def upgrade() -> None:
    op.execute(sa.text("UPDATE scenarios SET opening_message=:new_opening, batna=:new_batna WHERE slug='supplier-procurement' AND opening_message=:old_opening AND batna=:old_batna").bindparams(new_opening=NEW_OPENING, new_batna=NEW_BATNA, old_opening=OLD_OPENING, old_batna=OLD_BATNA))


def downgrade() -> None:
    op.execute(sa.text("UPDATE scenarios SET opening_message=:old_opening, batna=:old_batna WHERE slug='supplier-procurement' AND opening_message=:new_opening AND batna=:new_batna").bindparams(new_opening=NEW_OPENING, new_batna=NEW_BATNA, old_opening=OLD_OPENING, old_batna=OLD_BATNA))
