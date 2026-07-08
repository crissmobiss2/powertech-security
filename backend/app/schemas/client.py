import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class ClientCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    industry: Optional[str] = None
    risk_tier: str = "medium"
    billing_email: Optional[EmailStr] = None
    address: Optional[dict] = None
    sla_config: Optional[dict] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    industry: Optional[str] = None
    risk_tier: Optional[str] = None
    status: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    address: Optional[dict] = None
    sla_config: Optional[dict] = None
    notes: Optional[str] = None
    account_manager_id: Optional[uuid.UUID] = None


class ClientResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    industry: Optional[str]
    risk_tier: str
    status: str
    billing_email: Optional[str]
    address: Optional[dict]
    sla_config: Optional[dict]
    notes: Optional[str]
    account_manager_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
