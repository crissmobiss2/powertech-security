import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=30)
    address: Optional[dict] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    risk_level: str = "medium"
    timezone: str = "Asia/Manila"
    type: str = "office"
    emergency_contacts: Optional[list] = None
    notes: Optional[str] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    address: Optional[dict] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    risk_level: Optional[str] = None
    timezone: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    emergency_contacts: Optional[list] = None
    notes: Optional[str] = None


class SiteResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    name: str
    code: Optional[str]
    address: Optional[dict]
    latitude: Optional[float]
    longitude: Optional[float]
    risk_level: str
    timezone: str
    type: str
    status: str
    emergency_contacts: Optional[list]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
