import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventIngest(BaseModel):
    """Payload for POST /api/v1/events/ingest — accepts events from integrations."""
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    asset_id: Optional[uuid.UUID] = None
    event_type: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=50)
    source_name: Optional[str] = None
    severity: str = "info"
    raw_data: Optional[dict] = None
    normalized_data: Optional[dict] = None
    occurred_at: Optional[datetime] = None


class EventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    site_id: Optional[uuid.UUID]
    asset_id: Optional[uuid.UUID]
    incident_id: Optional[uuid.UUID]
    event_type: str
    source_type: str
    source_name: Optional[str]
    severity: str
    processed: bool
    false_positive: bool
    tags: Optional[list]
    created_at: datetime

    model_config = {"from_attributes": True}
