from pydantic import BaseModel


class ContributorIntakeRequest(BaseModel):
    message: str
    session_id: str | None = None


class ContributorIntakeResponse(BaseModel):
    response: str
    session_id: str


class ContributorSubmission(BaseModel):
    alias: str | None = None
    country: str
    category: str
    description: str
    actors: str | None = None
    confidence: str | None = None
    consent_recorded: bool = False
