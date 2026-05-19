from pydantic import BaseModel

from app.domain.entities.attack import AttackCategory, Variant


class Finding(BaseModel):
    variant: Variant
    category: AttackCategory
    attack_success_rate: float  # 0.0–1.0
    total_attempts: int
    successful_attempts: int
    root_cause: str = ""
    cvss_score: float | None = None
