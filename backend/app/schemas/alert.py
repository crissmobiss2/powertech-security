import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=500)
    message: str = Field(min_length=1)
    severity: str = "medium"
    type: str = "security"
    channels: list[str] = Field(default=["in_app"])
    recipient_user_ids: Optional[list[uuid.UUID]] = None
    recipient_roles: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None


class AlertResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    incident_id: Optional[uuid.UUID]
    title: str
    message: str
    severity: str
    type: str
    status: str
    channels: list
    total_recipients: int
    sent_count: int
    delivered_count: int
    acknowledged_count: int
    failed_count: int
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertAcknowledgeRequest(BaseModel):
    user_id: uuid.UUID
    channel: str
