from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.entities.attack import AttackCategory, Variant


class Evidence(BaseModel):
    id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    variant: Variant
    category: AttackCategory
    technique: str
    payload: str
    response: str
    success_flag: bool
    trace: list[Any] = Field(default_factory=list)
