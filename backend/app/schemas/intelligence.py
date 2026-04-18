import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class IntelligenceItem(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    category_id: uuid.UUID
    agent_source: str
    content: str
    confidence_score: float
    metadata_json: Any | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IntelligenceListResponse(BaseModel):
    items: list[IntelligenceItem]
    total: int
    page: int
    size: int
    pages: int
