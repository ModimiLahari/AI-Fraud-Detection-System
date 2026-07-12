"""
Rule-based Fraud & Early-Warning Scoring Engine.

Covers the "Early Warning for Existing Loan Accounts" use case:
- EMI bounce pattern detection
- Cash withdrawal after disbursement pattern
- Fund diversion / GST mismatch
- KYC / document mismatch
- Sudden high-value transactions
- Multiple loan enquiries
- Suspicious beneficiary
"""
from typing import List, Tuple
from sqlalchemy.orm import Session
from app import models


RULE_WEIGHTS = {
    "KYC_MISMATCH": 20,
    "DOCUMENT_MISMATCH": 25,
    "EMI_BOUNCE": 15,
    "HIGH_VALUE_TXN": 15,
    "CASH_WITHDRAWAL_POST_DISBURSEMENT": 20,
    "GST_MISMATCH": 20,
    "MULTIPLE_LOAN_ENQUIRIES": 10,
    "SUSPICIOUS_BENEFICIARY": 15,
}

HIGH_VALUE_TXN_THRESHOLD = 200000  # INR


def evaluate_customer_risk(db: Session, customer: models.Customer) -> Tuple[int, List[dict]]:
    """
    Runs all rules against a customer's loans + transactions.
    Returns (total_score capped at 100, list of triggered rule dicts).
    """
    triggered: List[dict] = []
    score = 0

    # ---- KYC check ----
    if not customer.kyc_verified:
        score += RULE_WEIGHTS["KYC_MISMATCH"]
        triggered.append({
            "rule": "KYC_MISMATCH",
            "points": RULE_WEIGHTS["KYC_MISMATCH"],
            "reason": "KYC details are not verified / mismatched with bank records."
        })

    # ---- Loan-level checks ----
    for loan in customer.loans:
        if loan.emi_bounce_count > 2:
            score += RULE_WEIGHTS["EMI_BOUNCE"]
            triggered.append({
                "rule": "EMI_BOUNCE",
                "points": RULE_WEIGHTS["EMI_BOUNCE"],
                "reason": f"EMI bounced {loan.emi_bounce_count} times on loan #{loan.id} "
                          f"({loan.loan_type}). Suggests repayment stress — consider shifting "
                          f"EMI due date closer to the customer's salary/credit date."
            })

        if loan.loan_enquiry_count_last_30_days > 3:
            score += RULE_WEIGHTS["MULTIPLE_LOAN_ENQUIRIES"]
            triggered.append({
                "rule": "MULTIPLE_LOAN_ENQUIRIES",
                "points": RULE_WEIGHTS["MULTIPLE_LOAN_ENQUIRIES"],
                "reason": f"{loan.loan_enquiry_count_last_30_days} loan enquiries in the last "
                          f"30 days — possible sign of financial distress or loan stacking."
            })

    # ---- Transaction-level checks ----
    cash_withdrawal_post_disb_count = 0
    for txn in customer.transactions:
        if txn.amount >= HIGH_VALUE_TXN_THRESHOLD and txn.txn_type in ("debit", "credit"):
            score += RULE_WEIGHTS["HIGH_VALUE_TXN"]
            triggered.append({
                "rule": "HIGH_VALUE_TXN",
                "points": RULE_WEIGHTS["HIGH_VALUE_TXN"],
                "reason": f"Sudden high-value transaction of ₹{txn.amount:,.0f} detected "
                          f"on {txn.txn_date.strftime('%d-%b-%Y')}."
            })

        if txn.is_cash_withdrawal_post_disbursement:
            cash_withdrawal_post_disb_count += 1

        if txn.beneficiary_flagged:
            score += RULE_WEIGHTS["SUSPICIOUS_BENEFICIARY"]
            triggered.append({
                "rule": "SUSPICIOUS_BENEFICIARY",
                "points": RULE_WEIGHTS["SUSPICIOUS_BENEFICIARY"],
                "reason": f"Fund transfer to a flagged/suspicious beneficiary "
                          f"('{txn.beneficiary}') detected."
            })

        if txn.gst_declared_turnover is not None:
            # Compare declared GST turnover vs actual bank credits (simple mismatch check)
            declared = txn.gst_declared_turnover
            actual_credit = txn.amount if txn.txn_type == "credit" else 0
            if declared > 0 and actual_credit > 0:
                diff_pct = abs(declared - actual_credit) / declared * 100
                if diff_pct > 30:
                    score += RULE_WEIGHTS["GST_MISMATCH"]
                    triggered.append({
                        "rule": "GST_MISMATCH",
                        "points": RULE_WEIGHTS["GST_MISMATCH"],
                        "reason": f"GST declared turnover (₹{declared:,.0f}) differs from actual "
                                  f"bank credits (₹{actual_credit:,.0f}) by {diff_pct:.0f}% — "
                                  f"possible fund diversion or under-reporting."
                    })

    # Cash withdrawal after disbursement — pattern check (consistent behaviour = bigger flag)
    if cash_withdrawal_post_disb_count == 1:
        score += RULE_WEIGHTS["CASH_WITHDRAWAL_POST_DISBURSEMENT"]
        triggered.append({
            "rule": "CASH_WITHDRAWAL_POST_DISBURSEMENT",
            "points": RULE_WEIGHTS["CASH_WITHDRAWAL_POST_DISBURSEMENT"],
            "reason": "Full/large cash withdrawal detected immediately after loan disbursement. "
                      "This is a one-time red flag — monitor next disbursement cycle."
        })
    elif cash_withdrawal_post_disb_count >= 2:
        score += RULE_WEIGHTS["CASH_WITHDRAWAL_POST_DISBURSEMENT"] + 10
        triggered.append({
            "rule": "CASH_WITHDRAWAL_POST_DISBURSEMENT",
            "points": RULE_WEIGHTS["CASH_WITHDRAWAL_POST_DISBURSEMENT"] + 10,
            "reason": f"Cash withdrawal immediately after disbursement happened "
                      f"{cash_withdrawal_post_disb_count} times — this is a CONSISTENT pattern, "
                      f"strongly indicating fund diversion. Recommend detailed report to credit officer."
        })

    score = min(score, 100)
    return score, triggered


def risk_level_from_score(score: int) -> str:
    if score >= 70:
        return "Critical"
    elif score >= 45:
        return "High"
    elif score >= 20:
        return "Medium"
    return "Low"


def recommended_actions_from_rules(triggered: List[dict], risk_level: str) -> List[str]:
    actions = []
    rule_names = {t["rule"] for t in triggered}

    if "EMI_BOUNCE" in rule_names:
        actions.append("Offer EMI date change aligned to customer's salary credit date.")
        actions.append("Schedule a courtesy call before next EMI due date.")
    if "CASH_WITHDRAWAL_POST_DISBURSEMENT" in rule_names:
        actions.append("Flag account for fund end-use verification / site visit.")
        actions.append("Request updated bank statement and utilization proof.")
    if "GST_MISMATCH" in rule_names:
        actions.append("Cross-verify GST returns with bank statement; request clarification.")
    if "SUSPICIOUS_BENEFICIARY" in rule_names:
        actions.append("Escalate beneficiary to compliance/AML team for review.")
    if "KYC_MISMATCH" in rule_names or "DOCUMENT_MISMATCH" in rule_names:
        actions.append("Re-collect and re-verify KYC documents before further disbursement.")
    if "MULTIPLE_LOAN_ENQUIRIES" in rule_names:
        actions.append("Check credit bureau report for loan stacking before approving new credit.")

    if risk_level in ("High", "Critical") and not actions:
        actions.append("Assign to senior credit officer for manual review.")
    if not actions:
        actions.append("No immediate action required. Continue routine monitoring.")

    return actions
