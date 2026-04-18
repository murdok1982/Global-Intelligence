import uuid
from datetime import datetime
from pydantic import BaseModel


class ChatSession(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    report_bind_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionCreate(BaseModel):
    report_id: uuid.UUID


class ChatMessage(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message: ChatMessage
    response: str


class ScenarioRequest(BaseModel):
    report_id: uuid.UUID
    variable: str


class ScenarioResponse(BaseModel):
    scenario_id: uuid.UUID
    output: str
