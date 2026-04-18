import uuid
from pydantic import BaseModel


class ContinentResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    country_count: int = 0

    model_config = {"from_attributes": True}


class ContinentDetail(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    country_count: int = 0

    model_config = {"from_attributes": True}
