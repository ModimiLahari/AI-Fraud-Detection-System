"""
Phase 1 — Deterministic Three-Pillar Fraud & Early-Warning Engine.

Design principles
-----------------
1. Rule engine is ENTIRELY deterministic. No AI/ML influences the score.
2. Each rule has a hard per-rule cap; pillar totals are capped independently.
3. One transaction / event cannot be double-counted across related rules.
   Related rules that fire on the same underlying event share an event_group_id;
   the engine accepts only the primary rule's points for that group.
4. AI explanation is called AFTER scoring is complete; it receives the
   deterministic output and may NOT alter any numeric value.
5. Every rule returns a RuleResult with full traceability fields.

Pillar caps
-----------
  P1  Repayment Conduct           : max 40 pts
  P2  Cashflow & End-Use Risk     : max 35 pts
  P3  Identity & Behavioural Risk : max 25 pts
  Composite = sum of capped pillars (max 100)

Phase 1 rules implemented
-------------------------
  P3  KYC_PENDING      :  0 pts  (Watch flag only — KYC in progress ≤ 30 days)
  P3  KYC_001          : 12 pts  KYC mismatch or pending > 30 days
  P3  IDENTITY_FRAUD   : 20 pts  confirmed / strongly indicated identity fraud
  P2  CASH_D_001       : 25 pts  post-disbursement cash withdrawal (ratio-based)
  P2  GST_M_001        : 20 pts  GST turnover vs adjusted operating bank credits
  P2  TXN_S_001        : 15 pts  borrower-relative transaction anomaly (median)
  P2  ENQ_M_001        : 12 pts  multiple bureau enquiry severity bands

Phase 2 rules (not yet implemented — stubs return not-triggered):
  EMI_B_001, EMI_B_002, EMI_D_001, EMI_LB_001, EMI_DATE_001

Phase 3 rules (not yet implemented):
  ROUND_001, BEN_F_001, REL_P_001, BEN_C_001, TXN_SPIKE_001
"""
from __future__ import annotations

import json
import statistics
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.models import NON_OPERATING_TXN_CATEGORIES

# ---------------------------------------------------------------------------
# Pillar caps
# ---------------------------------------------------------------------------
PILLAR_CAPS = {
    "Repayment Conduct": 40,
    "Cashflow & End-Use Risk": 35,
    "Identity & Behavioural Risk": 25,
}


# ---------------------------------------------------------------------------
# RuleResult dataclass — returned by every rule function
# ---------------------------------------------------------------------------
@dataclass
class RuleResult:
    rule_code: str
    pillar: str
    input_value: dict
    threshold: str
    points_awarded: int
    maximum_points: int
    severity: str                           # None|Watch|Low|Moderate|High|Critical
    reason: str
    recommended_action: str
    data_source: str
    data_quality: str = "sufficient"        # sufficient|partial|insufficient|unavailable
    supporting_signals: list = field(default_factory=list)
    event_group_id: Optional[str] = None    # set when rule shares event with another
    triggered: bool = True                  # False = evaluated but not triggered
    # Filled in by the engine after pillar accumulation
    pillar_raw_score: int = 0
    pillar_capped_score: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rule"] = self.rule_code
        data["points"] = self.points_awarded
        return data


# ---------------------------------------------------------------------------
# Helper: non-triggered audit entry
# ---------------------------------------------------------------------------
def _not_triggered(rule_code: str, pillar: str, reason: str,
                   data_source: str = "",
                   data_quality: str = "sufficient") -> RuleResult:
    return RuleResult(
        rule_code=rule_code,
        pillar=pillar,
        input_value={},
        threshold="",
        points_awarded=0,
        maximum_points=0,
        severity="None",
        reason=reason,
        recommended_action="",
        data_source=data_source,
        data_quality=data_quality,
        triggered=False,
    )


# ===========================================================================
# PILLAR 3 — Identity & Behavioural Risk  (max 25)
# ===========================================================================

def _rule_kyc(customer: models.Customer) -> RuleResult:
    """
    KYC_PENDING    (0 pts, Watch)    — documents in-progress, ≤ 30 days old
    KYC_001        (12 pts, High)    — mismatch, or pending beyond 30 days
    IDENTITY_FRAUD (20 pts, Critical)— confirmed / strongly indicated fraud

    Split rationale:
      'pending'  alone is not a risk; it is an operational state.
      'mismatch' signals that submitted documents do not match records
                 and amplifies all other risk signals.
      'fraud'    is a hard override; account must be frozen.
    """
    status = (customer.kyc_status or "verified").lower()
    onboarding_days = (datetime.utcnow() - customer.created_at).days

    if status == "fraud":
        return RuleResult(
            rule_code="IDENTITY_FRAUD",
            pillar="Identity & Behavioural Risk",
            input_value={
                "kyc_status": status,
                "customer_code": customer.customer_code,
            },
            threshold="kyc_status = fraud",
            points_awarded=20,
            maximum_points=20,
            severity="Critical",
            reason=(
                f"Identity fraud indicators confirmed for {customer.full_name}. "
                "All transactions and related accounts are suspect."
            ),
            recommended_action=(
                "Immediately freeze account. Escalate to AML/Compliance. "
                "File SAR with FIU-IND. Block all further disbursements."
            ),
            data_source=f"customer_id:{customer.id}",
            data_quality="sufficient",
        )

    if status == "mismatch":
        return RuleResult(
            rule_code="KYC_001",
            pillar="Identity & Behavioural Risk",
            input_value={
                "kyc_status": status,
                "customer_code": customer.customer_code,
            },
            threshold="kyc_status = mismatch",
            points_awarded=12,
            maximum_points=12,
            severity="High",
            reason=(
                f"KYC documents for {customer.full_name} do not match "
                "bank or bureau records. All other risk signals are "
                "amplified by unverified identity."
            ),
            recommended_action=(
                "Re-collect and re-verify KYC documents before any further "
                "disbursement. Flag for branch manager review."
            ),
            data_source=f"customer_id:{customer.id}",
            data_quality="sufficient",
        )

    if status == "pending":
        if onboarding_days <= 30:
            # Operational state — Watch flag, 0 pts
            return RuleResult(
                rule_code="KYC_PENDING",
                pillar="Identity & Behavioural Risk",
                input_value={
                    "kyc_status": status,
                    "onboarding_days": onboarding_days,
                },
                threshold="kyc_status = pending AND onboarding_days <= 30",
                points_awarded=0,
                maximum_points=0,
                severity="Watch",
                reason=(
                    f"KYC verification is in progress "
                    f"({onboarding_days} days since onboarding). "
                    "No score impact yet; monitor for completion."
                ),
                recommended_action=(
                    "Ensure KYC is completed within 30 days of account opening."
                ),
                data_source=f"customer_id:{customer.id}",
                data_quality="partial",
            )
        else:
            # Overdue pending → escalate to KYC_001 level
            return RuleResult(
                rule_code="KYC_001",
                pillar="Identity & Behavioural Risk",
                input_value={
                    "kyc_status": status,
                    "onboarding_days": onboarding_days,
                },
                threshold="kyc_status = pending AND onboarding_days > 30",
                points_awarded=12,
                maximum_points=12,
                severity="High",
                reason=(
                    f"KYC verification has been pending for {onboarding_days} "
                    "days, exceeding the 30-day limit. Treated as mismatch risk."
                ),
                recommended_action=(
                    "Immediately escalate to branch manager. "
                    "Block further disbursements until KYC is completed."
                ),
                data_source=f"customer_id:{customer.id}",
                data_quality="partial",
            )

    # verified — no issue
    return _not_triggered(
        "KYC_001",
        "Identity & Behavioural Risk",
        reason="KYC verified — no identity risk.",
        data_source=f"customer_id:{customer.id}",
    )


# ===========================================================================
# PILLAR 2 — Cashflow & End-Use Risk  (max 35)
# ===========================================================================

def _rule_cash_withdrawal(
        customer: models.Customer,
        loan: models.Loan,
        transactions: List[models.Transaction]) -> RuleResult:
    """
    CASH_D_001 — Post-disbursement cash withdrawal severity.

    Uses withdrawal-amount / loan-amount ratio (not absolute threshold).
    Pattern bonus (+5 pts) applied when 2+ events, capped at MAX_PTS.

    False-positive exclusions:
      • loan_type in {Cash Loan, Kisan Credit Card, Agriculture Loan}
        — cash disbursement is product design, not diversion
      • loan_amount < 50 000 — small-ticket personal borrowers commonly
        transact in cash; ratio-based rule still applies but suppressed
        to avoid excessive false positives
    """
    RULE = "CASH_D_001"
    PILLAR = "Cashflow & End-Use Risk"
    MAX_PTS = 25

    excluded_types = {"cash loan", "kisan credit card", "agriculture loan"}
    if loan.loan_type.lower() in excluded_types:
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                f"Loan type '{loan.loan_type}' — cash disbursement is "
                "product design, not end-use diversion."
            ),
            data_source=f"loan_id:{loan.id}",
        )

    if loan.loan_amount < 50_000:
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                "Loan amount < ₹50K — small-ticket borrowers commonly "
                "transact in cash; rule suppressed."
            ),
            data_source=f"loan_id:{loan.id}",
        )

    window_end = loan.disbursement_date + timedelta(days=30)
    post_txns = [
        t for t in transactions
        if (t.is_cash_withdrawal_post_disbursement
            and loan.disbursement_date <= t.txn_date <= window_end)
    ]

    if not post_txns:
        return _not_triggered(
            RULE, PILLAR,
            reason="No cash withdrawals detected within 30 days of disbursement.",
            data_source=f"loan_id:{loan.id}",
        )

    total_withdrawn = sum(t.amount for t in post_txns)
    ratio_pct = (total_withdrawn / loan.loan_amount) * 100
    event_count = len(post_txns)
    days_from_disb = min(
        (t.txn_date - loan.disbursement_date).days for t in post_txns
    )

    # Score tiers by ratio
    if ratio_pct < 20:
        pts, sev = 0, "Watch"
    elif ratio_pct < 50:
        pts, sev = 10, "Low"
    elif ratio_pct < 80:
        pts, sev = 18, "Moderate"
    else:
        pts, sev = 25, "Severe"

    # Pattern bonus: 2+ events → +5, capped at MAX_PTS
    if event_count >= 2 and pts > 0:
        pts = min(pts + 5, MAX_PTS)
        sev = "Critical" if pts >= MAX_PTS else sev

    txn_ids = [t.id for t in post_txns]
    return RuleResult(
        rule_code=RULE,
        pillar=PILLAR,
        input_value={
            "loan_amount": loan.loan_amount,
            "total_cash_withdrawn": total_withdrawn,
            "withdrawal_ratio_pct": round(ratio_pct, 1),
            "event_count": event_count,
            "earliest_days_from_disbursement": days_from_disb,
        },
        threshold=(
            "<20% Watch; 20-50% Low(10); 50-80% Moderate(18); "
            ">80% Severe(25); +5 if 2+ events (cap 25)"
        ),
        points_awarded=pts,
        maximum_points=MAX_PTS,
        severity=sev,
        reason=(
            f"Total cash withdrawal of ₹{total_withdrawn:,.0f} "
            f"({ratio_pct:.1f}% of ₹{loan.loan_amount:,.0f} loan) "
            f"across {event_count} event(s), earliest "
            f"{days_from_disb} day(s) after disbursement — "
            "indicates potential end-use violation."
        ),
        recommended_action=(
            "Initiate site visit within 5 working days. "
            "Request utilization certificate and business expenditure invoices."
            if sev in ("Moderate", "Severe", "Critical")
            else
            "Monitor next disbursement cycle; request brief utilization update."
        ),
        data_source=f"loan_id:{loan.id}, txn_ids:{txn_ids}",
        data_quality="sufficient",
        supporting_signals=[
            {"signal": f"Earliest withdrawal {days_from_disb}d post-disbursement"},
            {"signal": f"{event_count} cash-withdrawal event(s) in 30-day window"},
        ],
    )


def _rule_gst_mismatch(
        customer: models.Customer,
        loans: List[models.Loan],
        transactions: List[models.Transaction]) -> RuleResult:
    """
    GST_M_001 — Period-matched GST declared outward supply vs adjusted
    operating bank credits.

    Operating credits exclude NON_OPERATING_TXN_CATEGORIES (loan
    disbursements, inter-account transfers, capital introduction, refunds,
    reversals, asset sales, EMI repayments, institutional receipts).

    False-positive suppressions:
      • gst_assessment_period_months < 3  → insufficient data, suppress
      • gst_scheme = composition          → apply 40% tolerance
      • gst_scheme in {exempt, none}      → rule not applicable, suppress
      • no gst_annual_turnover            → suppress
    """
    RULE = "GST_M_001"
    PILLAR = "Cashflow & End-Use Risk"
    MAX_PTS = 20

    if not customer.gst_annual_turnover or customer.gst_annual_turnover <= 0:
        return _not_triggered(
            RULE, PILLAR,
            reason="GST annual turnover not recorded — rule suppressed.",
            data_source=f"customer_id:{customer.id}",
            data_quality="unavailable",
        )

    scheme = (customer.gst_scheme or "none").lower()
    if scheme in ("exempt", "none"):
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                f"Customer GST scheme is '{scheme}' — "
                "mismatch rule not applicable."
            ),
            data_source=f"customer_id:{customer.id}",
        )

    period_months = customer.gst_assessment_period_months or 0
    if period_months < 3:
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                f"GST assessment period only {period_months} month(s) — "
                "minimum 3 months required for a reliable comparison."
            ),
            data_source=f"customer_id:{customer.id}",
            data_quality="insufficient",
        )

    # Period window for bank-credit comparison.
    # Use DATE-level truncation (no time component) to avoid microsecond
    # drift between seed time and engine evaluation time causing boundary
    # transactions to be incorrectly excluded.
    # Add 1-day buffer so that a transaction seeded as "exactly N months ago"
    # is always inside the window regardless of clock drift.
    today = datetime.utcnow().date()
    cutoff_date = today - timedelta(days=period_months * 30 + 1)

    operating_credits = 0.0
    excluded_credits: List[dict] = []
    for t in transactions:
        if t.txn_type != "credit":
            continue
        if t.txn_date.date() < cutoff_date:
            continue
        if t.txn_category in NON_OPERATING_TXN_CATEGORIES:
            excluded_credits.append(
                {"category": t.txn_category, "amount": t.amount}
            )
            continue
        operating_credits += t.amount

    if operating_credits <= 0:
        return _not_triggered(
            RULE, PILLAR,
            reason="No operating bank credits found in the assessment period.",
            data_source=f"customer_id:{customer.id}",
            data_quality="insufficient",
        )

    mismatch_pct = (
        abs(customer.gst_annual_turnover - operating_credits)
        / customer.gst_annual_turnover * 100
    )

    # Composition scheme: 40% tolerance before triggering
    trigger_threshold = 30.0
    if scheme == "composition":
        trigger_threshold = 40.0

    if mismatch_pct < trigger_threshold:
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                f"GST vs operating credits mismatch {mismatch_pct:.1f}% — "
                f"within tolerance ({trigger_threshold:.0f}% for "
                f"'{scheme}' scheme)."
            ),
            data_source=f"customer_id:{customer.id}",
        )

    if mismatch_pct < 50:
        pts, sev = 12, "Moderate"
    else:
        pts, sev = 20, "High"

    excluded_total = sum(e["amount"] for e in excluded_credits)
    return RuleResult(
        rule_code=RULE,
        pillar=PILLAR,
        input_value={
            "gst_declared": customer.gst_annual_turnover,
            "operating_credits_in_period": round(operating_credits, 2),
            "mismatch_pct": round(mismatch_pct, 1),
            "period_months": period_months,
            "gst_scheme": scheme,
            "excluded_credit_count": len(excluded_credits),
            "excluded_credit_total": round(excluded_total, 2),
        },
        threshold=(
            f"Mismatch > {trigger_threshold:.0f}% after excluding "
            "non-operating credits: 30-50% = Moderate(12); >50% = High(20)"
        ),
        points_awarded=pts,
        maximum_points=MAX_PTS,
        severity=sev,
        reason=(
            f"GST declared turnover ₹{customer.gst_annual_turnover:,.0f} "
            f"vs operating bank credits ₹{operating_credits:,.0f} "
            f"over {period_months} months — {mismatch_pct:.1f}% mismatch "
            f"(after excluding {len(excluded_credits)} non-operating "
            f"credit(s) totalling ₹{excluded_total:,.0f}). "
            "Possible GST inflation for loan eligibility or "
            "undeclared cash income."
        ),
        recommended_action=(
            "Request GSTR-1 and GSTR-3B for the assessment period. "
            "Cross-verify against bank statement narrations and "
            "purchase register."
        ),
        data_source=f"customer_id:{customer.id}",
        data_quality="sufficient",
        supporting_signals=[
            {"signal": f"Non-operating credits excluded: {excluded_credits[:5]}"},
        ],
    )


def _rule_txn_anomaly(
        customer: models.Customer,
        loans: List[models.Loan],
        transactions: List[models.Transaction]) -> List[RuleResult]:
    """
    TXN_S_001 — Borrower-relative transaction anomaly detection.

    Uses the customer's own 90-day median operating transaction amount as
    baseline. Loan disbursements, salary credits, EMI repayments, and other
    non-operating categories are excluded from both baseline and detection.

    Max 2 triggers per assessment run.  Total cap: 15 pts.
    Event-group IDs are assigned so the engine does not double-count a
    transaction already scored by CASH_D_001.
    """
    RULE = "TXN_S_001"
    PILLAR = "Cashflow & End-Use Risk"
    MAX_PTS_PER_EVENT = 12
    MAX_PTS_TOTAL = 15

    EXCLUDED_CATEGORIES = NON_OPERATING_TXN_CATEGORIES | {
        "salary", "agricultural_purchase"
    }

    op_txns = [
        t for t in transactions
        if t.txn_category not in EXCLUDED_CATEGORIES
    ]

    if len(op_txns) < 3:
        return [_not_triggered(
            RULE, PILLAR,
            reason=(
                "Fewer than 3 operating transactions available — "
                "insufficient baseline for anomaly detection."
            ),
            data_source=f"customer_id:{customer.id}",
            data_quality="insufficient",
        )]

    # Use date-level cutoff (same approach as GST_M_001) to avoid
    # microsecond boundary drift excluding edge-case transactions.
    today = datetime.utcnow().date()
    cutoff_date_90d = today - timedelta(days=91)  # 1-day buffer
    baseline_txns = [t for t in op_txns if t.txn_date.date() >= cutoff_date_90d]

    if len(baseline_txns) < 3:
        return [_not_triggered(
            RULE, PILLAR,
            reason=(
                "Fewer than 3 operating transactions in 90-day window — "
                "baseline unreliable."
            ),
            data_source=f"customer_id:{customer.id}",
            data_quality="partial",
        )]

    # -----------------------------------------------------------------------
    # DIRECTION-AWARE BASELINE
    # Credits (income / inflows) must be compared against a credit-side
    # median.  Debits (payments / outflows) against a debit-side median.
    # Mixing directions creates false positives: routine ₹5-8K vendor
    # payments produce a low debit median, then legitimate ₹80K revenue
    # credits appear as 10-16x anomalies even though they are normal income.
    # -----------------------------------------------------------------------
    credit_baseline = [t.amount for t in baseline_txns if t.txn_type == "credit"]
    debit_baseline  = [t.amount for t in baseline_txns if t.txn_type in ("debit", "cash_withdrawal")]

    median_credit = statistics.median(credit_baseline) if len(credit_baseline) >= 2 else None
    median_debit  = statistics.median(debit_baseline)  if len(debit_baseline)  >= 2 else None

    # If one side has too few transactions to form a reliable baseline,
    # suppress anomaly detection for that direction only.
    if median_credit is None and median_debit is None:
        return [_not_triggered(
            RULE, PILLAR,
            reason="Insufficient transactions on both sides to build direction-aware baseline.",
            data_source=f"customer_id:{customer.id}",
            data_quality="insufficient",
        )]

    # Already-scored post-disbursement cash withdrawals — primary rule
    # CASH_D_001 owns these; TXN_S_001 must not double-count them.
    already_scored_ids = {
        t.id for t in transactions
        if t.is_cash_withdrawal_post_disbursement
    }

    anomalies = []
    for t in op_txns:
        if t.id in already_scored_ids:
            continue   # CASH_D_001 primary — skip

        # Choose the correct directional baseline
        if t.txn_type == "credit":
            if median_credit is None or median_credit <= 0:
                continue   # no credit baseline — cannot assess this txn
            baseline = median_credit
        else:
            if median_debit is None or median_debit <= 0:
                continue   # no debit baseline — cannot assess this txn
            baseline = median_debit

        ratio = t.amount / baseline
        if ratio >= 5 and t.amount >= 50_000:
            if ratio >= 10 and t.amount >= 1_00_000:
                pts, sev = 12, "High"
            else:
                pts, sev = 8, "Moderate"
            anomalies.append((ratio, pts, sev, t, baseline))

    if not anomalies:
        return [_not_triggered(
            RULE, PILLAR,
            reason=(
                "No transactions exceed 5× their direction-specific "
                "credit/debit median."
            ),
            data_source=f"customer_id:{customer.id}",
        )]

    anomalies.sort(key=lambda x: x[0], reverse=True)
    results: List[RuleResult] = []
    accumulated = 0
    group_prefix = str(uuid.uuid4())[:8]

    for idx, (ratio, pts, sev, t, baseline) in enumerate(anomalies[:2]):
        remaining = MAX_PTS_TOTAL - accumulated
        pts = min(pts, remaining, MAX_PTS_PER_EVENT)
        if pts <= 0:
            break
        accumulated += pts

        direction = "credit" if t.txn_type == "credit" else "debit"
        results.append(RuleResult(
            rule_code=RULE,
            pillar=PILLAR,
            input_value={
                "txn_id": t.id,
                "txn_amount": t.amount,
                "txn_direction": direction,
                "direction_median_baseline": round(baseline, 2),
                "anomaly_ratio": round(ratio, 1),
                "txn_category": t.txn_category,
                "txn_date": t.txn_date.isoformat(),
            },
            threshold=(
                "Direction-aware: ratio ≥5× AND amount ≥₹50K → Moderate(8); "
                "ratio ≥10× AND amount ≥₹1L → High(12); "
                "max 2 events, total cap 15"
            ),
            points_awarded=pts,
            maximum_points=MAX_PTS_PER_EVENT,
            severity=sev,
            reason=(
                f"{direction.capitalize()} of ₹{t.amount:,.0f} is "
                f"{ratio:.1f}× this customer's 90-day {direction} median "
                f"of ₹{baseline:,.0f} "
                f"(category: {t.txn_category}, "
                f"date: {t.txn_date.strftime('%d-%b-%Y')}) — "
                "unexplained relative to borrower's own transaction pattern."
            ),
            recommended_action=(
                "Request purpose and supporting invoice / "
                "documentation for this transaction."
            ),
            data_source=f"customer_id:{customer.id}, txn_id:{t.id}",
            data_quality="sufficient",
            event_group_id=f"{group_prefix}-{idx}",
        ))

    return results


def _rule_enquiries(customer: models.Customer) -> RuleResult:
    """
    ENQ_M_001 — Multiple bureau enquiry severity bands.

    Customer-level (not loan-level). Rate-shopping enquiries (same loan
    type within 14-day window) are suppressed at data-entry time via
    BureauEnquiry.is_rate_shopping and excluded from these counts by the
    seeding / data-ingestion layer.
    """
    RULE = "ENQ_M_001"
    PILLAR = "Cashflow & End-Use Risk"
    MAX_PTS = 12

    raw_30d = customer.bureau_enquiry_count_30d or 0
    raw_60d = customer.bureau_enquiry_count_60d or 0
    raw_90d = customer.bureau_enquiry_count_90d or 0

    if raw_30d == 0 and raw_90d == 0:
        return _not_triggered(
            RULE, PILLAR,
            reason="No bureau enquiries in 90-day window.",
            data_source=f"customer_id:{customer.id}",
        )

    # Severity bands (highest band across all windows wins)
    if raw_30d >= 7 or raw_90d >= 10:
        pts, sev = 12, "High"
    elif raw_30d >= 5 or raw_90d >= 7:
        pts, sev = 8, "Moderate"
    elif raw_30d >= 3 or raw_90d >= 5:
        pts, sev = 4, "Low"
    else:
        return _not_triggered(
            RULE, PILLAR,
            reason=(
                f"{raw_30d} enquiry(ies) in 30d, {raw_90d} in 90d — "
                "within normal range."
            ),
            data_source=f"customer_id:{customer.id}",
        )

    return RuleResult(
        rule_code=RULE,
        pillar=PILLAR,
        input_value={
            "enquiries_30d": raw_30d,
            "enquiries_60d": raw_60d,
            "enquiries_90d": raw_90d,
        },
        threshold=(
            "3+/30d or 5+/90d → Low(4); "
            "5+/30d or 7+/90d → Moderate(8); "
            "7+/30d or 10+/90d → High(12)"
        ),
        points_awarded=pts,
        maximum_points=MAX_PTS,
        severity=sev,
        reason=(
            f"{raw_30d} bureau enquiry(ies) in last 30 days, "
            f"{raw_90d} in 90 days — elevated credit-seeking behaviour "
            "suggesting possible financial distress or loan-stacking risk."
        ),
        recommended_action=(
            "Pull full bureau report; verify whether new loans were "
            "sanctioned post-enquiry before extending further credit."
        ),
        data_source=f"customer_id:{customer.id}",
        data_quality="sufficient" if raw_90d > 0 else "partial",
    )


# ===========================================================================
# MAIN ENGINE
# ===========================================================================

def evaluate_customer_risk(
        db: Session,
        customer: models.Customer,
) -> Tuple[int, List[RuleResult]]:
    """
    Run all Phase 1 rules against the customer.

    Returns
    -------
    (composite_score, all_results)
        all_results includes both triggered and non-triggered rules for
        full audit coverage.

    Scoring algorithm
    -----------------
    1. Collect RuleResult from each rule (triggered=True/False).
    2. For triggered results: if two results share an event_group_id,
       only the first (primary) contributes points; the rest contribute 0.
    3. Accumulate raw pillar totals.
    4. Cap each pillar independently (P1=40, P2=35, P3=25).
    5. composite = sum of capped pillar scores.
    6. Annotate every result with the pillar raw/capped state at that point
       (for RuleAuditTrail persistence).
    """
    loans = customer.loans
    transactions = customer.transactions
    all_results: List[RuleResult] = []

    # -- Pillar 3 — Identity & Behavioural Risk ------------------------------
    all_results.append(_rule_kyc(customer))

    # -- Pillar 2 — Cashflow & End-Use Risk ----------------------------------
    for loan in loans:
        all_results.append(
            _rule_cash_withdrawal(customer, loan, transactions)
        )

    all_results.append(_rule_gst_mismatch(customer, loans, transactions))
    all_results.extend(_rule_txn_anomaly(customer, loans, transactions))
    all_results.append(_rule_enquiries(customer))

    # -- Score accumulation with event-group dedup ---------------------------
    pillar_raw: dict = {p: 0 for p in PILLAR_CAPS}
    seen_groups: set = set()

    for result in all_results:
        if not result.triggered:
            continue
        pts = result.points_awarded
        if result.event_group_id:
            if result.event_group_id in seen_groups:
                pts = 0   # secondary rule in this group — no points
            else:
                seen_groups.add(result.event_group_id)
        pillar_raw[result.pillar] = pillar_raw.get(result.pillar, 0) + pts

    # -- Cap each pillar -----------------------------------------------------
    pillar_capped = {
        p: min(raw, PILLAR_CAPS[p])
        for p, raw in pillar_raw.items()
    }
    composite = sum(pillar_capped.values())

    # -- Annotate every result with pillar context (for audit trail) ---------
    running_raw: dict = {p: 0 for p in PILLAR_CAPS}
    running_capped: dict = {p: 0 for p in PILLAR_CAPS}
    seen_groups2: set = set()

    for result in all_results:
        if not result.triggered:
            result.pillar_raw_score = pillar_raw.get(result.pillar, 0)
            result.pillar_capped_score = pillar_capped.get(result.pillar, 0)
            continue
        pts = result.points_awarded
        if result.event_group_id:
            if result.event_group_id in seen_groups2:
                pts = 0
            else:
                seen_groups2.add(result.event_group_id)

        running_raw[result.pillar] = running_raw.get(result.pillar, 0) + pts
        running_capped[result.pillar] = min(
            running_raw[result.pillar],
            PILLAR_CAPS.get(result.pillar, 999),
        )
        result.pillar_raw_score = running_raw[result.pillar]
        result.pillar_capped_score = running_capped[result.pillar]

    return composite, [result.to_dict() for result in all_results]


def risk_level_from_score(score: int) -> str:
    if score >= 70:
        return "Critical"
    elif score >= 45:
        return "High"
    elif score >= 20:
        return "Medium"
    return "Low"


def recommended_actions_from_rules(
        results: List[dict],
        risk_level: str) -> List[str]:
    """Aggregate recommended actions from triggered rules, deduplicated."""
    actions: List[str] = []
    seen: set = set()
    for r in results:
        if r.get("triggered") and r.get("recommended_action"):
            action = r["recommended_action"].strip()
            if action and action not in seen:
                seen.add(action)
                actions.append(action)
    if risk_level in ("High", "Critical") and not actions:
        actions.append(
            "Assign to senior credit officer for manual review."
        )
    if not actions:
        actions.append(
            "No immediate action required. Continue routine monitoring."
        )
    return actions
