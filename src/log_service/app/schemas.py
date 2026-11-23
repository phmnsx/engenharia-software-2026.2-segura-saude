from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class AuditLogIn(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    actor_id: str
    actor_role: str
    action: str
    resource: str
    status: Literal["SUCCESS", "DENIED", "ERROR"]
    details: dict[str, Any] = Field(default_factory=dict)


class SystemLogIn(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    service_name: str
    level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class LogCreatedOut(BaseModel):
    id: int
    event_id: UUID
    timestamp: datetime
