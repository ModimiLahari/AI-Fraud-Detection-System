from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class TriggeredRuleIn(BaseModel):
    rule: str
    points: int
    detail: str


class RecommendationIn(BaseModel):
    action: str
    reason: str
    priority: str = "medium"


class PdfReportRequest(BaseModel):
    """Optional body — if omitted, router falls back to DB-only data (no AI text)."""
    triggered_rules: List[TriggeredRuleIn] = Field(default_factory=list)
    ai_explanation: Optional[str] = None
    recommendations: List[RecommendationIn] = Field(default_factory=list)


class EmailAlertRequest(BaseModel):
    customer_id: int
    to_email: EmailStr
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    message: str
    attach_pdf: bool = False


class EmailAlertResponse(BaseModel):
    sent: bool
    reason: Optional[str] = None
