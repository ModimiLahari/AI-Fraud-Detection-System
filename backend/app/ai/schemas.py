from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TriggeredRule(BaseModel):
    rule: str
    points: int
    detail: str


class ExplainRequest(BaseModel):
    triggered_rules: List[TriggeredRule] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)


class ExplainResponse(BaseModel):
    customer_id: int
    explanation: str
    tier: Literal["Low", "Medium", "High", "Critical"]
    source: Literal["gemini", "offline"]


class RecommendRequest(BaseModel):
    triggered_rules: List[TriggeredRule] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)


class RecommendedAction(BaseModel):
    action: str
    reason: str
    priority: Literal["high", "medium", "low"]


class RecommendResponse(BaseModel):
    customer_id: int
    recommendations: List[RecommendedAction]
    source: Literal["gemini", "offline"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantRequest(BaseModel):
    question: str
    triggered_rules: List[TriggeredRule] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)
    history: List[ChatTurn] = Field(default_factory=list)


class AssistantResponse(BaseModel):
    customer_id: int
    answer: str
    source: Literal["gemini", "offline"]


class EmiPaymentHistory(BaseModel):
    payment_dates: List[str]
    due_day: int = Field(ge=1, le=28)


class EmiPatternResponse(BaseModel):
    customer_id: int
    pattern: Literal["consistent_late", "consistent_on_time", "irregular", "insufficient_data"]
    avg_days_late: float
    suggested_new_due_day: Optional[int]
    note: str


class WithdrawalRecord(BaseModel):
    date: str
    amount: float
    days_after_disbursement: int


class WithdrawalHistory(BaseModel):
    withdrawals: List[WithdrawalRecord]
    disbursement_amount: float


class WithdrawalPatternResponse(BaseModel):
    customer_id: int
    pattern: Literal["full_withdrawal_immediate", "consistent_partial_withdrawal", "normal_usage", "insufficient_data"]
    total_withdrawn_pct: float
    is_red_flag: bool
    note: str
