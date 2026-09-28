"""Add configurable session duration and two negotiation scenarios.

Revision ID: 20260928_0012
Revises: 20260927_0011
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260928_0012"
down_revision: Union[str, None] = "20260927_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RENT_ID = "44444444-4444-4444-8444-444444444444"
TEAM_ID = "55555555-5555-4555-8555-555555555555"


def upgrade() -> None:
    op.add_column(
        "negotiation_sessions",
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="10"),
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
    op.bulk_insert(scenarios, [
        {
            "id": RENT_ID,
            "slug": "office-lease",
            "name": "Условия аренды офиса",
            "description": "Договоритесь с арендодателем о ставке, сроке договора и условиях переезда команды.",
            "character_name": "Дмитрий Орлов",
            "character_role": "Собственник офисного помещения",
            "opening_message": (
                "Офис готов к въезду. Ставка — 180 тысяч рублей в месяц, "
                "депозит за два месяца и договор минимум на год. "
                "Вы просили пересмотреть условия. Что предлагаете?"
            ),
            "hidden_goal": (
                "Найти надёжного арендатора на длительный срок: помещение пустует "
                "два месяца, а регулярные платежи важнее максимальной ставки."
            ),
            "constraints": (
                "Ставка не ниже 160 тысяч рублей в месяц. Депозит можно разделить "
                "на два платежа; арендные каникулы — не более двух недель. "
                "Снижение ставки возможно в обмен на договор на 18 месяцев."
            ),
            "batna": (
                "Продолжить поиск арендатора через агентство, потратив ещё "
                "один-два месяца без арендного дохода и заплатив комиссию."
            ),
            "difficulty": "medium",
            "user_goals": [
                "Снизить ежемесячную ставку или расходы на переезд",
                "Согласовать посильный депозит и понятные условия договора",
                "Не брать на себя обязательства без встречных уступок",
            ],
            "system_prompt": (
                "Ты — Дмитрий Орлов, собственник офиса. Собеседник представляет "
                "компанию-арендатора. Обсуждай ставку, депозит, арендные каникулы "
                "и срок договора. Цени предсказуемость платежей и долгосрочность. "
                "Не уступай без встречного условия и соблюдай ограничения. "
                "Не раскрывай скрытую цель и альтернативу сразу: отвечай на "
                "содержательные вопросы о мотивах и других вариантах."
            ),
            "initial_metrics": {
                "trust": 58, "irritation": 30, "interest": 70,
                "tension": 40, "openness": 56, "risk": 34,
            },
            "completion_rules": {"max_turns": 12, "allow_manual_finish": True},
        },
        {
            "id": TEAM_ID,
            "slug": "team-conflict",
            "name": "Конфликт в команде",
            "description": "Разрешите спор о распределении задач и договоритесь с коллегой о совместной работе.",
            "character_name": "Анна Лебедева",
            "character_role": "Коллега — ведущий специалист команды",
            "opening_message": (
                "Опять срочные задачи достались мне, а приоритеты поменяли без "
                "обсуждения. Я больше не готова подхватывать чужую работу. "
                "Как мы будем с этим разбираться?"
            ),
            "hidden_goal": (
                "Получить признание своей нагрузки и прозрачное распределение "
                "ответственности, сохранив время для ключевого проекта."
            ),
            "constraints": (
                "На этой неделе нет ресурсов для найма. Коллега может взять "
                "не более одной дополнительной задачи, если другая будет "
                "снята или перенесена. Переработки неприемлемы."
            ),
            "batna": (
                "Отказаться от дополнительных задач и попросить руководителя "
                "формально перераспределить работу, даже если общий срок сдвинется."
            ),
            "difficulty": "medium",
            "user_goals": [
                "Выяснить причины недовольства, не переходя на обвинения",
                "Согласовать приоритеты и конкретное распределение задач",
                "Восстановить рабочие отношения и договориться о правилах на будущее",
            ],
            "system_prompt": (
                "Ты — Анна Лебедева, перегруженный ведущий специалист. Собеседник "
                "— твой коллега, с которым нужно договориться о задачах. В начале "
                "ты раздражена несправедливым распределением нагрузки. Становись "
                "открытее в ответ на признание проблемы, вопросы и конкретный "
                "план. Сопротивляйся давлению, обесцениванию и пустым обещаниям. "
                "Не принимай работу сверх ограничений. Не раскрывай скрытую "
                "цель и альтернативу сразу; обсуждай их после уместных вопросов."
            ),
            "initial_metrics": {
                "trust": 52, "irritation": 48, "interest": 62,
                "tension": 52, "openness": 46, "risk": 42,
            },
            "completion_rules": {"max_turns": 12, "allow_manual_finish": True},
        },
    ])


def downgrade() -> None:
    connection = op.get_bind()
    parameters = {"rent_id": RENT_ID, "team_id": TEAM_ID}
    in_use = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM negotiation_sessions "
        "WHERE scenario_id IN (CAST(:rent_id AS UUID), CAST(:team_id AS UUID)))"
    ).bindparams(**parameters)).scalar_one()
    if in_use:
        raise RuntimeError("Cannot remove scenarios with existing negotiation sessions")
    connection.execute(sa.text(
        "DELETE FROM scenarios WHERE id IN (CAST(:rent_id AS UUID), CAST(:team_id AS UUID))"
    ).bindparams(**parameters))
    op.drop_column("negotiation_sessions", "duration_minutes")
