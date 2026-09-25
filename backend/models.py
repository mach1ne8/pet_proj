import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.postgresql import JSONB

from core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "scenarios.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    final_score: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="analyst")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hint_history: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    batna_revealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("negotiation_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fork_from_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    scenario: Mapped["Scenario"] = relationship(
        back_populates="sessions",
    )

    state: Mapped["SessionState"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    result: Mapped["SessionResult"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    metric_events: Mapped[list["SessionMetricEvent"]] = relationship(
        cascade="all, delete-orphan",
    )


class SessionState(Base):
    __tablename__ = "session_states"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "negotiation_sessions.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    metrics: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
    )

    turn_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    detected_tactics: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    coach_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    session: Mapped["NegotiationSession"] = relationship(
        back_populates="state",
    )


class SessionMetricEvent(Base):
    __tablename__ = "session_metric_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    turn_count: Mapped[int] = mapped_column(nullable=False)
    metrics: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    deltas: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    detected_tactics: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    coach_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class SessionResult(Base):
    __tablename__ = "session_results"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    final_score: Mapped[int] = mapped_column(nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    final_metrics: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    mistakes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    recommendations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    key_moments: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    skills: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    analysis_status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    session: Mapped["NegotiationSession"] = relationship(
        back_populates="result",
    )


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    character_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    character_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    opening_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    hidden_goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    constraints: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    batna: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    difficulty: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    user_goals: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )

    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    initial_metrics: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
    )

    completion_rules: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )

    sessions: Mapped[list["NegotiationSession"]] = relationship(
        back_populates="scenario",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "negotiation_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    session: Mapped["NegotiationSession"] = relationship(
        back_populates="messages",
    )
