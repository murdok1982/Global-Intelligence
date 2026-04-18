import uuid
from typing import Any
from pydantic import BaseModel


class CountryProfile(BaseModel):
    overall_risk_score: str | None = None
    metadata_json: str | None = None

    model_config = {"from_attributes": True}


class CountryResponse(BaseModel):
    id: uuid.UUID
    name: str
    iso_code: str
    continent_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class CountryDetail(BaseModel):
    id: uuid.UUID
    name: str
    iso_code: str
    continent_id: uuid.UUID | None = None
    profile: CountryProfile | None = None

    model_config = {"from_attributes": True}
