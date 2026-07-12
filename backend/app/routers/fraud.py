import json
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, fraud_engine, ai_explain, reports_pdf

router = APIRouter(prefix="/fraud", tags=["Fraud"])


def _get_customer_or_404(customer_id: int, db: Session) -> models.Customer:
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _run_and_save_score(customer: models.Customer, db: Session) -> models.FraudReport:
    score, triggered = fraud_engine.evaluate_customer_risk(db, customer)
    risk_level = fraud_engine.risk_level_from_score(score)
    actions = fraud_engine.recommended_actions_from_rules(triggered, risk_level)
    ai_text = ai_explain.generate_ai_explanation(customer.full_name, score, risk_level, triggered)

    report = models.FraudReport(
        customer_id=customer.id,
        risk_score=score,
        risk_level=risk_level,
        triggered_rules=json.dumps(triggered),
        ai_explanation=ai_text,
        recommended_actions=json.dumps(actions),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if risk_level in ("High", "Critical"):
        alert = models.Alert(
            customer_id=customer.id,
            title=f"{risk_level} risk detected — {customer.full_name}",
            message=f"Risk score {score}/100. " + (triggered[0]["reason"] if triggered else ""),
            severity=risk_level,
        )
        db.add(alert)
        db.commit()

    return report


@router.post("/check-loan-application", response_model=schemas.FraudReportOut)
def check_loan_application(
    payload: schemas.FraudCheckLoanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = _get_customer_or_404(payload.customer_id, db)
    loan = db.query(models.Loan).filter(
        models.Loan.id == payload.loan_id, models.Loan.customer_id == customer.id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found for this customer")

    return _run_and_save_score(customer, db)


@router.post("/check-transaction", response_model=schemas.FraudReportOut)
def check_transaction(
    payload: schemas.FraudCheckTransactionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = _get_customer_or_404(payload.customer_id, db)
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == payload.transaction_id, models.Transaction.customer_id == customer.id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found for this customer")

    return _run_and_save_score(customer, db)


@router.post("/generate-score", response_model=schemas.FraudReportOut)
def generate_score(
    payload: schemas.FraudScoreRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = _get_customer_or_404(payload.customer_id, db)
    return _run_and_save_score(customer, db)


@router.get("/report/{customer_id}", response_model=schemas.FraudReportOut)
def get_latest_report(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_customer_or_404(customer_id, db)
    report = (
        db.query(models.FraudReport)
        .filter(models.FraudReport.customer_id == customer_id)
        .order_by(models.FraudReport.id.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No fraud report generated yet for this customer")
    return report


@router.get("/report/{customer_id}/history", response_model=List[schemas.FraudReportOut])
def get_report_history(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_customer_or_404(customer_id, db)
    return (
        db.query(models.FraudReport)
        .filter(models.FraudReport.customer_id == customer_id)
        .order_by(models.FraudReport.generated_at.asc())
        .all()
    )


@router.get("/reasons/{customer_id}")
def get_reasons(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_customer_or_404(customer_id, db)
    report = (
        db.query(models.FraudReport)
        .filter(models.FraudReport.customer_id == customer_id)
        .order_by(models.FraudReport.id.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No fraud report generated yet for this customer")

    return {
        "customer_id": customer_id,
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
        "reasons": json.loads(report.triggered_rules) if report.triggered_rules else [],
        "ai_explanation": report.ai_explanation,
        "recommended_actions": json.loads(report.recommended_actions) if report.recommended_actions else [],
    }


@router.get("/alerts", response_model=List[schemas.AlertOut])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()


@router.put("/alerts/{alert_id}/read", response_model=schemas.AlertOut)
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/dashboard-summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customers = db.query(models.Customer).all()
    latest_report_by_customer = {}
    for report in db.query(models.FraudReport).order_by(models.FraudReport.id.asc()).all():
        latest_report_by_customer[report.customer_id] = report

    risk_distribution = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0, "Not Evaluated": 0}
    branch_wise_risk = {}
    scored = 0
    total_score = 0

    for customer in customers:
        branch = customer.branch or "Unassigned"
        branch_wise_risk.setdefault(branch, {"Low": 0, "Medium": 0, "High": 0, "Critical": 0})

        report = latest_report_by_customer.get(customer.id)
        if report:
            risk_distribution[report.risk_level] = risk_distribution.get(report.risk_level, 0) + 1
            branch_wise_risk[branch][report.risk_level] = branch_wise_risk[branch].get(report.risk_level, 0) + 1
            scored += 1
            total_score += report.risk_score
        else:
            risk_distribution["Not Evaluated"] += 1

    total_alerts = db.query(models.Alert).count()
    unread_alerts = db.query(models.Alert).filter(models.Alert.is_read == False).count()  # noqa: E712

    return {
        "total_customers": len(customers),
        "scored_customers": scored,
        "unscored_customers": len(customers) - scored,
        "average_risk_score": round(total_score / scored, 1) if scored else 0,
        "risk_distribution": risk_distribution,
        "branch_wise_risk": branch_wise_risk,
        "total_alerts": total_alerts,
        "unread_alerts": unread_alerts,
    }


@router.post("/ai-assistant/{customer_id}")
def ai_assistant(
    customer_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = _get_customer_or_404(customer_id, db)
    question = payload.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="'question' is required")

    report = (
        db.query(models.FraudReport)
        .filter(models.FraudReport.customer_id == customer_id)
        .order_by(models.FraudReport.id.desc())
        .first()
    )
    context = {
        "customer_name": customer.full_name,
        "score": report.risk_score if report else 0,
        "risk_level": report.risk_level if report else "Low",
        "triggered_rules": json.loads(report.triggered_rules) if report and report.triggered_rules else [],
    }
    answer = ai_explain.ai_chat_answer(question, context)
    return {"customer_id": customer_id, "question": question, "answer": answer}


@router.get("/report/{customer_id}/pdf")
def download_pdf_report(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = _get_customer_or_404(customer_id, db)
    report = (
        db.query(models.FraudReport)
        .filter(models.FraudReport.customer_id == customer_id)
        .order_by(models.FraudReport.id.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No fraud report generated yet for this customer")

    pdf_bytes = reports_pdf.build_fraud_pdf_report(customer, report)
    filename = f"fraud_report_{customer.customer_code}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/report/excel/all")
def download_excel_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customers = db.query(models.Customer).all()
    latest_report_by_customer = {}
    for report in db.query(models.FraudReport).order_by(models.FraudReport.id.asc()).all():
        latest_report_by_customer[report.customer_id] = report

    customers_with_reports = [(c, latest_report_by_customer.get(c.id)) for c in customers]
    xlsx_bytes = reports_pdf.build_fraud_excel_report(customers_with_reports)
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="fraud_portfolio_export.xlsx"'},
    )
