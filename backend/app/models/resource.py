
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceStatus(str, Enum):
    UNKNOWN = "unknown"
    SYNCED = "synced"
    DRIFTED = "drifted"
    RECONCILING = "reconciling"
    FAILED = "failed"


class Resource(BaseModel):
    id: str
    name: str
    provider: str
    environment: str

    desired_state: dict[str, Any] = Field(
        default_factory=dict
    )

    observed_state: dict[str, Any] = Field(
        default_factory=dict
    )

    status: ResourceStatus = ResourceStatus.UNKNOWN

    last_reconciled: datetime | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
