import uuid
from pydantic import BaseModel, EmailStr
from app.models.user import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: RoleEnum
    is_active: bool

    model_config = {"from_attributes": True}
