"""
Conversational AI Assistant — powers the "Why is this customer high risk?"
chat widget on the Customer Detail screen. Stateless per-call: the frontend
sends the running history each time (kept short) plus the new question.
"""

import logging
from typing import List, Dict, Any

from app.ai.gemini_client import gemini_client, GeminiUnavailable
from app.ai.prompts import build_assistant_prompt
from app.ai.explanation_engine import _offline_explanation, _risk_tier

logger = logging.getLogger("ai.assistant")

MAX_HISTORY_TURNS = 6


def _offline_answer(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]],
                     risk_score: int, question: str) -> str:
    base = _offline_explanation(customer, triggered_rules, risk_score)
    q = question.lower().strip()

    if any(k in q for k in ["why", "risk", "flag"]):
        return base
    if any(k in q for k in ["what should", "recommend", "action", "do next"]):
        return (
            "Based on the triggered rules, prioritize the highest-point factor first "
            "(see the Recommended Actions panel for the ranked list). "
            f"Overall tier is {_risk_tier(risk_score)}."
        )
    if any(k in q for k in ["score", "how risky"]):
        return f"Current risk score is {risk_score}/100, tier: {_risk_tier(risk_score)}."
    return (
        "I can only answer from the data already on this customer's profile — "
        f"currently: risk score {risk_score}/100 ({_risk_tier(risk_score)} tier) with "
        f"{len(triggered_rules)} rule(s) triggered. Ask me why they're flagged, what to "
        "do next, or about a specific triggered rule."
    )


def ask_assistant(
    customer: Dict[str, Any],
    triggered_rules: List[Dict[str, Any]],
    risk_score: int,
    question: str,
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """
    history: list of {"role": "user"|"assistant", "content": str}, most recent last.
    Returns {"answer": str, "source": "gemini"|"offline"}
    """
    history = (history or [])[-MAX_HISTORY_TURNS:]
    prompt = build_assistant_prompt(customer, triggered_rules, risk_score, history, question)

    try:
        answer = gemini_client.generate(prompt, max_output_tokens=300)
        return {"answer": answer, "source": "gemini"}
    except GeminiUnavailable as exc:
        logger.info("Assistant falling back to offline answer: %s", exc)
        return {"answer": _offline_answer(customer, triggered_rules, risk_score, question), "source": "offline"}
