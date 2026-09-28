import uuid

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionStateResponse(BaseModel):
    metrics: dict[str, int]
    turn_count: int
    detected_tactics: list[str]
    coach_message: str
    signal: str | None = None


class SessionResultResponse(BaseModel):
    final_score: int
    outcome: str
    final_metrics: dict[str, int]
    strengths: list[str]
    mistakes: list[str]
    recommendations: list[str]
    key_moments: list[str] = Field(default_factory=list)
    skills: dict[str, int] = Field(default_factory=dict)
    achievements: list[str] = Field(default_factory=list)
    analysis_status: Literal["pending", "ready", "failed"] = "ready"
    completed_at: datetime


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str = "active"
    scenario_id: uuid.UUID | None = None
    difficulty: str = "analyst"
    duration_minutes: int = 10
    expires_at: datetime | None = None
    hints_used: int = 0
    hint_history: list[str] = Field(default_factory=list)
    batna_revealed: bool = False
    batna_text: str | None = None
    notes: str = ""
    parent_session_id: uuid.UUID | None = None
    fork_from_turn: int | None = None
    state: SessionStateResponse | None = None
    result: SessionResultResponse | None = None
    messages: list[MessageResponse]


class CreateSessionRequest(BaseModel):
    scenario_id: uuid.UUID | None = None
    difficulty: Literal["beginner", "analyst", "advanced", "expert"] = "analyst"
    duration_minutes: int = Field(default=10, ge=10, le=60, strict=True)


class ForkSessionRequest(BaseModel):
    turn_count: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=5000)


class NotesRequest(BaseModel):
    notes: str = Field(max_length=5000)


class HintResponse(BaseModel):
    message: str
    hints_used: int
    history: list[str] = Field(default_factory=list)


class SuggestionRequest(BaseModel):
    tactic: Literal["open_question", "interests", "facts", "compromise"]


class SuggestionResponse(BaseModel):
    message: str


class ScenarioSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    character_name: str
    character_role: str
    difficulty: str


class ChatRequest(BaseModel):
    session_id: uuid.UUID

    message: str = Field(
        min_length=1,
        max_length=5000,
    )


class ChatResponse(BaseModel):
    message: str
    state: SessionStateResponse
    batna_revealed: bool = False
    batna_text: str | None = None


class CreateProfileReportRequest(BaseModel):
    session_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class ProfileAnalysisResponse(BaseModel):
    summary: str
    strengths: list[str]
    growth_areas: list[str]
    next_steps: list[str]
    rounds_analyzed: int


class ProfileReportResponse(BaseModel):
    report_id: uuid.UUID
    status: Literal["pending", "ready", "failed"]
    analysis: ProfileAnalysisResponse | None = None
