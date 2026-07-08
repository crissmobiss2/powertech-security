import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    type: str
    sub_type: Optional[str] = None
    status: str = "online"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    purchase_date: Optional[date] = None
    warranty_expires: Optional[date] = None
    location_detail: Optional[str] = None
    floor: Optional[str] = None
    zone: Optional[str] = None
    tags: Optional[list] = None
    metadata: Optional[dict] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    site_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    location_detail: Optional[str] = None
    floor: Optional[str] = None
    zone: Optional[str] = None
    tags: Optional[list] = None
    metadata: Optional[dict] = None


class AssetStatusUpdate(BaseModel):
    status: str
    last_seen_at: Optional[datetime] = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID]
    name: str
    code: Optional[str]
    type: str
    sub_type: Optional[str]
    status: str
    ip_address: Optional[str]
    mac_address: Optional[str]
    serial_number: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    firmware_version: Optional[str]
    purchase_date: Optional[date]
    warranty_expires: Optional[date]
    location_detail: Optional[str]
    floor: Optional[str]
    zone: Optional[str]
    last_seen_at: Optional[datetime]
    tags: Optional[list]
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
