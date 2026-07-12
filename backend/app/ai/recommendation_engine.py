"""
Recommendation Engine: converts triggered rules -> ranked action list for the
Credit/Fraud Officer. Tries Gemini for natural phrasing; always has a static
rule -> action lookup table as fallback so recommendations are never empty.
"""

import logging
from typing import List, Dict, Any

from app.ai.gemini_client import gemini_client, GeminiUnavailable
from app.ai.prompts import build_recommendation_prompt

logger = logging.getLogger("ai.recommendation_engine")

# Static fallback mapping — mirrors the exact scoring rules from the Fraud Rule Engine.
# Keyed by a normalized rule name so it survives minor wording differences.
RULE_ACTION_MAP = {
    "kyc_mismatch": {
        "action": "Re-verify KYC documents with customer in person",
        "reason": "KYC details do not match records on file",
        "priority": "high",
    },
    "document_mismatch": {
        "action": "Request original documents for manual verification",
        "reason": "Submitted documents show mismatches",
        "priority": "high",
    },
    "emi_bounce": {
        "action": "Call customer to confirm income cycle and shift EMI due date",
        "reason": "More than 2 EMI bounces detected",
        "priority": "high",
    },
    "high_value_transaction": {
        "action": "Flag account for transaction monitoring for 30 days",
        "reason": "Sudden high-value transaction detected",
        "priority": "medium",
    },
    "cash_withdrawal_after_disbursement": {
        "action": "Schedule urgent call to confirm fund utilization",
        "reason": "Cash withdrawn shortly after loan disbursement",
        "priority": "high",
    },
    "gst_turnover_mismatch": {
        "action": "Request updated GST returns and bank statement reconciliation",
        "reason": "GST turnover does not match bank credits",
        "priority": "medium",
    },
    "multiple_loan_enquiries": {
        "action": "Check credit bureau report for parallel loan applications",
        "reason": "Multiple loan enquiries in a short window",
        "priority": "medium",
    },
    "suspicious_beneficiary": {
        "action": "Escalate beneficiary details to fraud investigation team",
        "reason": "Beneficiary flagged as suspicious",
        "priority": "high",
    },
}


def _normalize(rule_name: str) -> str:
    return rule_name.strip().lower().replace(" ", "_").replace("-", "_")


def _offline_recommendations(triggered_rules: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not triggered_rules:
        return [{
            "action": "Continue standard periodic monitoring",
            "reason": "No fraud rules currently triggered",
            "priority": "low",
        }]

    ranked = sorted(triggered_rules, key=lambda r: r["points"], reverse=True)
    recs = []
    seen = set()
    for rule in ranked:
        key = _normalize(rule["rule"])
        mapped = RULE_ACTION_MAP.get(key)
        if not mapped:
            mapped = {
                "action": f"Review flagged condition: {rule['rule']}",
                "reason": rule.get("detail", rule["rule"]),
                "priority": "medium",
            }
        if mapped["action"] in seen:
            continue
        seen.add(mapped["action"])
        recs.append(mapped)
        if len(recs) == 4:
            break
    return recs


def get_recommendations(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]], risk_score: int) -> Dict[str, Any]:
    """Returns {"recommendations": [{"action","reason","priority"}, ...], "source": "gemini"|"offline"}"""
    prompt = build_recommendation_prompt(customer, triggered_rules, risk_score)
    try:
        parsed = gemini_client.generate_json(prompt)
        if isinstance(parsed, list) and parsed:
            cleaned = []
            for item in parsed[:4]:
                if isinstance(item, dict) and "action" in item:
                    cleaned.append({
                        "action": str(item.get("action", ""))[:120],
                        "reason": str(item.get("reason", ""))[:150],
                        "priority": item.get("priority", "medium") if item.get("priority") in ("high", "medium", "low") else "medium",
                    })
            if cleaned:
                return {"recommendations": cleaned, "source": "gemini"}
        raise GeminiUnavailable("Unparseable or empty JSON from Gemini")
    except GeminiUnavailable as exc:
        logger.info("Falling back to offline recommendations: %s", exc)
        return {"recommendations": _offline_recommendations(triggered_rules), "source": "offline"}
