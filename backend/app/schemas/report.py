import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    report_date: datetime
    executive_summary: str
    published: bool
    signature_fingerprint: Optional[str] = None
    signed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportDetail(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    report_date: datetime
    executive_summary: str
    content_json: str
    published: bool
    signature: Optional[str] = None
    signature_fingerprint: Optional[str] = None
    signed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    country_iso: str
