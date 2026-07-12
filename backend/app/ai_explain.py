"""
AI Explanation Layer.

Uses Google Gemini API to turn rule-engine output into a human-readable
risk explanation for the Credit/Risk officer. Falls back to a deterministic
template-based explanation if no API key is configured or the API call
fails (so the demo never breaks without internet).
"""
import json
from typing import List
import requests
from app.config import settings


def _offline_explanation(customer_name: str, score: int, risk_level: str, triggered: List[dict]) -> str:
    if not triggered:
        return (
            f"{customer_name}'s account shows no significant risk indicators at this time. "
            f"Risk score is {score}/100 ({risk_level}). Recommend continuing routine monitoring."
        )

    reasons = "; ".join([t["reason"] for t in triggered[:4]])
    return (
        f"{customer_name} has a risk score of {score}/100, classified as {risk_level} risk. "
        f"This is primarily driven by: {reasons}. "
        f"These patterns together suggest heightened repayment or fraud risk and warrant "
        f"closer monitoring by the credit officer before further exposure is extended."
    )


def generate_ai_explanation(customer_name: str, score: int, risk_level: str, triggered: List[dict]) -> str:
    if not settings.GEMINI_API_KEY:
        return _offline_explanation(customer_name, score, risk_level, triggered)

    rules_text = "\n".join([f"- {t['rule']} (+{t['points']} pts): {t['reason']}" for t in triggered]) or "None"

    prompt = (
        "You are a bank fraud & credit risk assistant. Explain in 3-4 clear, professional "
        "sentences (for a bank credit officer, not a technical audience) why this customer "
        f"received a risk score of {score}/100 ({risk_level} risk). "
        f"Customer: {customer_name}.\n"
        f"Triggered rules:\n{rules_text}\n"
        "Be specific, avoid jargon, and end with a one-line overall recommendation."
    )

    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception:
        # Never let a demo fail because of network/API issues
        return _offline_explanation(customer_name, score, risk_level, triggered)


def ai_chat_answer(question: str, context: dict) -> str:
    """
    Powers the 'AI Assistant' widget — "Why is this customer high risk?"
    context = {customer_name, score, risk_level, triggered_rules: [...]}
    """
    if not settings.GEMINI_API_KEY:
        return _offline_explanation(
            context.get("customer_name", "This customer"),
            context.get("score", 0),
            context.get("risk_level", "Low"),
            context.get("triggered_rules", []),
        )

    prompt = (
        "You are an AI fraud-risk assistant embedded in a bank dashboard. "
        f"Context about the customer (JSON): {json.dumps(context)}\n"
        f"Officer's question: {question}\n"
        "Answer concisely and professionally in 2-4 sentences, referring only to the given context."
    )
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return _offline_explanation(
            context.get("customer_name", "This customer"),
            context.get("score", 0),
            context.get("risk_level", "Low"),
            context.get("triggered_rules", []),
        )
