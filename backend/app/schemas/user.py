import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = None
    role: str = "soc_analyst"
    client_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    client_id: Optional[uuid.UUID] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    avatar_url: Optional[str]
    role: str
    status: str
    mfa_enabled: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
