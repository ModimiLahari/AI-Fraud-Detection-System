"""
Turns Rule-Engine output (Module 1) into a human-readable explanation.
Tries Gemini first; falls back to a deterministic templated explanation
built directly from the triggered rules so the demo NEVER shows a blank
or broken AI panel even with zero internet / no API key.
"""

import logging
from typing import List, Dict, Any

from app.ai.gemini_client import gemini_client, GeminiUnavailable
from app.ai.prompts import build_explanation_prompt

logger = logging.getLogger("ai.explanation_engine")


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def _offline_explanation(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]], risk_score: int) -> str:
    tier = _risk_tier(risk_score)
    name = customer.get("name", "This customer")

    if not triggered_rules:
        return (
            f"{name} has a risk score of {risk_score}/100 ({tier}). "
            f"No fraud-rule conditions were triggered based on current data — "
            f"continue standard monitoring."
        )

    ranked = sorted(triggered_rules, key=lambda r: r["points"], reverse=True)
    lead = ranked[0]
    lines = [
        f"{name} is flagged as {tier} risk with a score of {risk_score}/100, "
        f"driven mainly by: {lead['rule']} (+{lead['points']} points — {lead['detail']})."
    ]
    if len(ranked) > 1:
        others = "; ".join(f"{r['rule']} (+{r['points']})" for r in ranked[1:])
        lines.append(f"Additional contributing factors: {others}.")
    lines.append(
        f"Overall tier: {tier}. Most urgent factor to review first: {lead['rule']}."
    )
    return " ".join(lines)


def explain_risk(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]], risk_score: int) -> Dict[str, Any]:
    """
    customer: dict with at least id, name, branch, loan_amount
    triggered_rules: list of {"rule": str, "points": int, "detail": str}
    risk_score: int total score from the rule engine (0-100)

    Returns: {"explanation": str, "tier": str, "source": "gemini" | "offline"}
    """
    prompt = build_explanation_prompt(customer, triggered_rules, risk_score)
    try:
        text = gemini_client.generate(prompt)
        return {"explanation": text, "tier": _risk_tier(risk_score), "source": "gemini"}
    except GeminiUnavailable as exc:
        logger.info("Falling back to offline explanation: %s", exc)
        return {
            "explanation": _offline_explanation(customer, triggered_rules, risk_score),
            "tier": _risk_tier(risk_score),
            "source": "offline",
        }
