"""
Reports Router — mounts under /reports in main.py:

    from app.reports.router import router as reports_router
    app.include_router(reports_router)

Wiring assumptions (same as Module 3):
- app.database.get_db                    -> SQLAlchemy session dependency
- app.models.Customer                    -> id, name, branch, loan_amount
- app.models.FraudReport                 -> customer_id, risk_score, triggered_rules (JSON list)
- app.models.Alert                       -> id, customer_id, severity, message, created_at
- app.auth.dependencies.get_current_user -> JWT dependency

If a FraudReport row isn't found for a customer, risk_score defaults to 0 and
triggered_rules to [] so the PDF/Excel still generate instead of erroring —
useful for demoing a "clean" customer report.
"""

import json
import logging
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, FraudReport, Alert
from app.auth import get_current_user

from app.reports.pdf_generator import build_customer_pdf
from app.reports.excel_generator import build_portfolio_excel
from app.reports.email_service import send_alert_email
from app.reports.schemas import PdfReportRequest, EmailAlertRequest, EmailAlertResponse

logger = logging.getLogger("reports.router")

router = APIRouter(prefix="/reports", tags=["Reports & Alerts"])


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


def _rules_list(report) -> list:
    """FraudReport.triggered_rules is stored as a JSON-encoded string, not a list."""
    raw = getattr(report, "triggered_rules", None) if report else None
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return []
    # fraud_engine.py (Module 1) stores each rule as {"rule","points","reason"};
    # the PDF/Excel generators expect a "detail" key -- normalize so both work.
    for r in raw:
        if "detail" not in r and "reason" in r:
            r["detail"] = r["reason"]
    return raw


def _latest_fraud_report(customer_id: int, db: Session):
    return (
        db.query(FraudReport)
        .filter(FraudReport.customer_id == customer_id)
        .order_by(FraudReport.id.desc())
        .first()
    )


@router.post("/pdf/{customer_id}")
def download_pdf_report(customer_id: int, payload: PdfReportRequest = PdfReportRequest(),
                         db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One-click PDF fraud report for a single customer. Streams the file directly."""
    customer = _get_customer_or_404(customer_id, db)
    report = _latest_fraud_report(customer_id, db)

    risk_score = getattr(report, "risk_score", 0) if report else 0
    triggered_rules = payload.triggered_rules and [r.model_dump() for r in payload.triggered_rules]
    if not triggered_rules:
        triggered_rules = _rules_list(report)

    pdf_bytes = build_customer_pdf(
        customer=_customer_dict(customer),
        risk_score=risk_score,
        triggered_rules=triggered_rules,
        ai_explanation=payload.ai_explanation,
        recommendations=[r.model_dump() for r in payload.recommendations],
    )

    filename = f"fraud_report_{customer.id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/excel")
def download_portfolio_excel(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Portfolio-wide Excel export — all customers + recent alerts + summary sheet."""
    customers = db.query(Customer).all()
    reports_by_customer = {
        r.customer_id: r for r in db.query(FraudReport).all()
    }

    customer_rows: List[dict] = []
    for c in customers:
        report = reports_by_customer.get(c.id)
        risk_score = getattr(report, "risk_score", 0) if report else 0
        rules = _rules_list(report)
        top_rule = max(rules, key=lambda r: r.get("points", 0))["rule"] if rules else "—"
        customer_rows.append({
            "id": c.id, "name": getattr(c, "name", ""), "branch": getattr(c, "branch", ""),
            "loan_amount": getattr(c, "loan_amount", ""), "risk_score": risk_score, "top_rule": top_rule,
        })

    alert_rows = []
    for a in db.query(Alert).order_by(Alert.id.desc()).limit(500).all():
        cust = db.query(Customer).filter(Customer.id == a.customer_id).first()
        alert_rows.append({
            "id": a.id,
            "customer_name": getattr(cust, "name", "Unknown") if cust else "Unknown",
            "severity": getattr(a, "severity", ""),
            "message": getattr(a, "message", ""),
            "created_at": str(getattr(a, "created_at", "")),
        })

    xlsx_bytes = build_portfolio_excel(customer_rows, alert_rows)
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="fraud_portfolio_export.xlsx"'},
    )


@router.post("/email-alert", response_model=EmailAlertResponse)
def email_alert(payload: EmailAlertRequest, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    """Send a real-time email alert, optionally with the customer's PDF report attached."""
    customer = _get_customer_or_404(payload.customer_id, db)
    report = _latest_fraud_report(payload.customer_id, db)
    risk_score = getattr(report, "risk_score", 0) if report else 0

    pdf_bytes = None
    if payload.attach_pdf:
        triggered_rules = _rules_list(report)
        pdf_bytes = build_customer_pdf(
            customer=_customer_dict(customer), risk_score=risk_score, triggered_rules=triggered_rules,
        )

    result = send_alert_email(
        to_email=payload.to_email,
        customer_name=getattr(customer, "name", "Unknown"),
        severity=payload.severity,
        message=payload.message,
        risk_score=risk_score,
        pdf_bytes=pdf_bytes,
        pdf_filename=f"fraud_report_{customer.id}.pdf",
    )
    return EmailAlertResponse(**result)
