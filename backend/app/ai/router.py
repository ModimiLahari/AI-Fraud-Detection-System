"""
AI Router — mounts under /ai in main.py:

    from app.ai.router import router as ai_router
    app.include_router(ai_router)

Wiring assumptions (matching Module 1's backend structure):
- app.database.get_db            -> SQLAlchemy session dependency
- app.models.Customer            -> Customer ORM model (id, name, branch, loan_amount, ...)
- app.auth.dependencies.get_current_user -> JWT-protected user dependency

If your Module 1 file/module names differ slightly, only the three imports
below need adjusting — nothing else in this file depends on their internals
beyond `customer.id / .name / .branch / .loan_amount`.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer
from app.auth import get_current_user

from app.ai.explanation_engine import explain_risk
from app.ai.recommendation_engine import get_recommendations
from app.ai.assistant import ask_assistant
from app.ai.pattern_detectors import analyze_emi_pattern, analyze_withdrawal_pattern
from app.ai.schemas import (
    ExplainRequest, ExplainResponse,
    RecommendRequest, RecommendResponse,
    AssistantRequest, AssistantResponse,
    EmiPaymentHistory, EmiPatternResponse,
    WithdrawalHistory, WithdrawalPatternResponse,
)

logger = logging.getLogger("ai.router")

router = APIRouter(prefix="/ai", tags=["AI Layer"])


def _get_customer_or_404(customer_id: int, db: Session) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


def _customer_dict(customer: Customer) -> dict:
    latest_loan = max(customer.loans, key=lambda l: l.id) if customer.loans else None
    return {
        "id": customer.id,
        "name": getattr(customer, "full_name", "Unknown"),
        "branch": getattr(customer, "branch", "N/A"),
        "loan_amount": latest_loan.loan_amount if latest_loan else "N/A",
    }


@router.post("/explain/{customer_id}", response_model=ExplainResponse)
def explain(customer_id: int, payload: ExplainRequest,
            db: Session = Depends(get_db), user=Depends(get_current_user)):
    """AI Explanation: why is this customer flagged as risky."""
    customer = _get_customer_or_404(customer_id, db)
    rules = [r.model_dump() for r in payload.triggered_rules]
    result = explain_risk(_customer_dict(customer), rules, payload.risk_score)
    return ExplainResponse(customer_id=customer_id, **result)


@router.post("/recommend/{customer_id}", response_model=RecommendResponse)
def recommend(customer_id: int, payload: RecommendRequest,
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Recommendation Engine: ranked next-best-actions for the credit officer."""
    customer = _get_customer_or_404(customer_id, db)
    rules = [r.model_dump() for r in payload.triggered_rules]
    result = get_recommendations(_customer_dict(customer), rules, payload.risk_score)
    return RecommendResponse(customer_id=customer_id, **result)


@router.post("/assistant/{customer_id}", response_model=AssistantResponse)
def assistant(customer_id: int, payload: AssistantRequest,
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    """AI Assistant chat widget: 'Why is this customer high risk?' and follow-ups."""
    customer = _get_customer_or_404(customer_id, db)
    rules = [r.model_dump() for r in payload.triggered_rules]
    history = [h.model_dump() for h in payload.history]
    result = ask_assistant(_customer_dict(customer), rules, payload.risk_score, payload.question, history)
    return AssistantResponse(customer_id=customer_id, **result)


@router.post("/emi-pattern/{customer_id}", response_model=EmiPatternResponse)
def emi_pattern(customer_id: int, payload: EmiPaymentHistory,
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Track-4 solution 1: detect EMI bounce/late pattern and suggest a better due date.
    """
    _get_customer_or_404(customer_id, db)
    result = analyze_emi_pattern(payload.payment_dates, payload.due_day)
    return EmiPatternResponse(customer_id=customer_id, **result)


@router.post("/withdrawal-pattern/{customer_id}", response_model=WithdrawalPatternResponse)
def withdrawal_pattern(customer_id: int, payload: WithdrawalHistory,
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Track-4 solution 2: detect full/consistent post-disbursement cash withdrawal
    and flag it for the Credit Officer.
    """
    _get_customer_or_404(customer_id, db)
    withdrawals = [w.model_dump() for w in payload.withdrawals]
    result = analyze_withdrawal_pattern(withdrawals, payload.disbursement_amount)
    return WithdrawalPatternResponse(customer_id=customer_id, **result)
