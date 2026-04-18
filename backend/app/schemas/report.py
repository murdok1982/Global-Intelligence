import uuid
from datetime import datetime
from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    report_date: datetime
    executive_summary: str
    published: bool

    model_config = {"from_attributes": True}


class ReportDetail(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    report_date: datetime
    executive_summary: str
    content_json: str
    published: bool

    model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    country_iso: str
