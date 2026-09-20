import uuid

from datetime import datetime

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


class SessionResultResponse(BaseModel):
    final_score: int
    outcome: str
    final_metrics: dict[str, int]
    strengths: list[str]
    mistakes: list[str]
    recommendations: list[str]
    completed_at: datetime


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str = "active"
    scenario_id: uuid.UUID | None = None
    state: SessionStateResponse | None = None
    result: SessionResultResponse | None = None
    messages: list[MessageResponse]


class CreateSessionRequest(BaseModel):
    scenario_id: uuid.UUID | None = None


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
