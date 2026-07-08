import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlaybookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    trigger_type: str
    trigger_config: Optional[dict] = None
    conditions: Optional[dict] = None
    actions: list[dict] = Field(default_factory=list)
    enabled: bool = True


class PlaybookUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    trigger_config: Optional[dict] = None
    conditions: Optional[dict] = None
    actions: Optional[list[dict]] = None
    enabled: Optional[bool] = None


class PlaybookResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_config: Optional[dict]
    conditions: Optional[dict]
    actions: list
    enabled: bool
    run_count: int
    last_triggered_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlaybookExecuteRequest(BaseModel):
    trigger_event: Optional[dict] = None
    incident_id: Optional[uuid.UUID] = None


class PlaybookExecutionResponse(BaseModel):
    id: uuid.UUID
    playbook_id: uuid.UUID
    tenant_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    steps_completed: Optional[list]
    results: Optional[dict]

    model_config = {"from_attributes": True}
