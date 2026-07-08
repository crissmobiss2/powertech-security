import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    asset_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    type: str = "support"
    priority: str = "medium"
    assigned_to: Optional[uuid.UUID] = None
    sla_due_at: Optional[datetime] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    sla_due_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    client_notes: Optional[str] = None
    labor_hours: Optional[float] = None
    parts_used: Optional[list] = None
    cost: Optional[float] = None


class TicketCheckinRequest(BaseModel):
    notes: Optional[str] = None


class TicketCheckoutRequest(BaseModel):
    resolution_notes: Optional[str] = None
    labor_hours: Optional[float] = None
    parts_used: Optional[list] = None


class TicketSignoffRequest(BaseModel):
    signed_by: str = Field(min_length=2, max_length=200)


class TicketCommentCreate(BaseModel):
    content: str = Field(min_length=1)
    is_internal: bool = False


class TicketResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID]
    incident_id: Optional[uuid.UUID]
    asset_id: Optional[uuid.UUID]
    title: str
    description: Optional[str]
    type: str
    status: str
    priority: str
    assigned_to: Optional[uuid.UUID]
    sla_due_at: Optional[datetime]
    checkin_at: Optional[datetime]
    checkout_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    client_signoff_at: Optional[datetime]
    client_signoff_by: Optional[str]
    labor_hours: Optional[float]
    parts_used: Optional[list]
    cost: Optional[float]
    resolution_notes: Optional[str]
    client_notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
