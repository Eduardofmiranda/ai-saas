from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    data: Optional[dict[str, Any]] = None
    trigger_type: Optional[str] = "message"
    trigger_config: Optional[dict[str, Any]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    active: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: str
    data: dict[str, Any]
    trigger_type: str
    trigger_config: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
