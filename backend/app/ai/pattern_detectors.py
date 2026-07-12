"""
Implements the two specific AI detections requested for the "Early Warning for
Existing Loan Accounts" use case:

1. EMI bounce pattern detection -> suggest a better EMI due date.
2. Post-disbursement cash withdrawal pattern detection -> flag full/consistent
   withdrawal and generate a detailed note for the Credit Officer.

Both use Gemini for the natural-language "note" field but compute the actual
pattern/percentages deterministically in Python first, so the numeric output
is always correct even if Gemini is unavailable — Gemini is only asked to
summarize numbers we already calculated, never to invent them.
"""

import logging
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.ai.gemini_client import gemini_client, GeminiUnavailable
from app.ai.prompts import build_emi_pattern_prompt, build_withdrawal_pattern_prompt

logger = logging.getLogger("ai.pattern_detectors")

DATE_FMT = "%Y-%m-%d"


def _parse(d: str) -> Optional[datetime]:
    try:
        return datetime.strptime(d, DATE_FMT)
    except (ValueError, TypeError):
        return None


def analyze_emi_pattern(payment_dates: List[str], due_day: int) -> Dict[str, Any]:
    """
    payment_dates: list of "YYYY-MM-DD" strings, actual dates EMIs were paid.
    due_day: the contractual due day of month (1-28).

    Returns dict with pattern, avg_days_late, suggested_new_due_day, note.
    """
    parsed = [p for p in (_parse(d) for d in payment_dates) if p]
    if len(parsed) < 2:
        result = {
            "pattern": "insufficient_data",
            "avg_days_late": 0,
            "suggested_new_due_day": None,
            "note": "Not enough payment history to detect a pattern yet.",
        }
        return result

    days_late = [p.day - due_day for p in parsed]
    avg_late = round(statistics.mean(days_late), 1)
    late_count = sum(1 for d in days_late if d > 2)
    on_time_count = sum(1 for d in days_late if abs(d) <= 2)

    if late_count >= max(2, len(days_late) // 2):
        pattern = "consistent_late"
        suggested_day = max(1, min(28, due_day + max(3, round(avg_late))))
    elif on_time_count == len(days_late):
        pattern = "consistent_on_time"
        suggested_day = None
    else:
        pattern = "irregular"
        suggested_day = None

    computed = {
        "pattern": pattern,
        "avg_days_late": avg_late,
        "suggested_new_due_day": suggested_day,
    }

    prompt = build_emi_pattern_prompt(payment_dates, due_day)
    try:
        ai_result = gemini_client.generate_json(prompt)
        note = ai_result.get("note") if ai_result else None
    except GeminiUnavailable:
        note = None

    if not note:
        if pattern == "consistent_late":
            note = (
                f"Customer pays ~{avg_late} days late on average. Consider moving the "
                f"due date to day {suggested_day} to align with their cash flow."
            )
        elif pattern == "consistent_on_time":
            note = "Payments are consistently on time — no due-date change needed."
        else:
            note = "Payment timing is irregular — monitor for another billing cycle before adjusting."

    computed["note"] = note
    return computed


def analyze_withdrawal_pattern(withdrawals: List[Dict[str, Any]], disbursement_amount: float) -> Dict[str, Any]:
    """
    withdrawals: list of {"date": "YYYY-MM-DD", "amount": float, "days_after_disbursement": int}
    disbursement_amount: float, the loan amount disbursed.

    Returns dict with pattern, total_withdrawn_pct, is_red_flag, note.
    """
    if not withdrawals or disbursement_amount <= 0:
        return {
            "pattern": "insufficient_data",
            "total_withdrawn_pct": 0,
            "is_red_flag": False,
            "note": "No withdrawal activity recorded since disbursement.",
        }

    total_withdrawn = sum(w.get("amount", 0) for w in withdrawals)
    pct = round(min(100.0, (total_withdrawn / disbursement_amount) * 100), 1)
    quick_withdrawals = [w for w in withdrawals if w.get("days_after_disbursement", 999) <= 2]
    quick_pct = round(min(100.0, sum(w.get("amount", 0) for w in quick_withdrawals) / disbursement_amount * 100), 1)

    if quick_pct >= 80:
        pattern = "full_withdrawal_immediate"
        is_red_flag = True
    elif pct >= 60 and len(withdrawals) >= 3:
        pattern = "consistent_partial_withdrawal"
        is_red_flag = True
    else:
        pattern = "normal_usage"
        is_red_flag = False

    prompt = build_withdrawal_pattern_prompt(withdrawals, disbursement_amount)
    try:
        ai_result = gemini_client.generate_json(prompt)
        note = ai_result.get("note") if ai_result else None
    except GeminiUnavailable:
        note = None

    if not note:
        if pattern == "full_withdrawal_immediate":
            note = f"{quick_pct}% of the loan was withdrawn within 2 days of disbursement — send report to Credit Officer."
        elif pattern == "consistent_partial_withdrawal":
            note = f"{pct}% withdrawn across {len(withdrawals)} transactions — recurring pattern, worth reviewing fund usage."
        else:
            note = f"Only {pct}% withdrawn so far — usage looks normal."

    return {
        "pattern": pattern,
        "total_withdrawn_pct": pct,
        "is_red_flag": is_red_flag,
        "note": note,
    }
