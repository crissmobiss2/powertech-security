import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    severity: str = "medium"
    type: str = "operational"
    source: str = "manual"
    assigned_to: Optional[uuid.UUID] = None
    tags: Optional[list] = None
    metadata: Optional[dict] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    escalated_to: Optional[uuid.UUID] = None
    tags: Optional[list] = None
    resolution_summary: Optional[str] = None


class IncidentTimelineEntry(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    event_type: str
    description: str
    metadata: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID]
    title: str
    description: Optional[str]
    severity: str
    status: str
    type: str
    source: str
    assigned_to: Optional[uuid.UUID]
    escalated_to: Optional[uuid.UUID]
    sla_due_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    resolution_summary: Optional[str]
    tags: Optional[list]
    metadata: Optional[dict]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentCloseRequest(BaseModel):
    resolution_summary: str = Field(min_length=10)
    status: str = "closed"  # closed or false_positive


class CommentCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    metadata: Optional[dict] = None
