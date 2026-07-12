"""
All prompt construction lives here so it's easy to tune without touching
transport code or business logic. Every prompt is built purely from data
already computed by the Rule Engine (Module 1) — the AI layer never invents
risk factors, it only explains / prioritizes ones that were already scored.
"""

from typing import List, Dict, Any


def build_explanation_prompt(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]], risk_score: int) -> str:
    rules_text = "\n".join(
        f"- {r['rule']}: +{r['points']} points ({r['detail']})" for r in triggered_rules
    ) or "- No rules triggered"

    return f"""You are a fraud & credit-risk analyst assistant embedded in a bank's
Early Warning System dashboard. Explain risk findings to a Credit/Fraud Officer
who is busy and non-technical about ML — be concrete, cite the actual numbers given,
and never invent facts not present below.

Customer: {customer.get('name', 'N/A')} (ID: {customer.get('id', 'N/A')})
Branch: {customer.get('branch', 'N/A')}
Loan Amount: {customer.get('loan_amount', 'N/A')}
Total Risk Score: {risk_score}/100

Triggered rules (each already scored by the rule engine):
{rules_text}

Write a 3-5 sentence plain-English explanation of WHY this customer is flagged,
in order of severity. End with one sentence stating the overall risk tier
(Low <30, Medium 30-59, High 60-79, Critical 80+) and the single most urgent
factor the officer should look at first. Do not use markdown headers."""


def build_recommendation_prompt(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]], risk_score: int) -> str:
    rules_text = "\n".join(f"- {r['rule']} (+{r['points']})" for r in triggered_rules) or "- none"

    return f"""You are advising a bank Credit Officer on next actions for a flagged loan
account. Based ONLY on the triggered rules below, return a JSON array of 2-4
recommended actions, ordered by priority. Each item must have:
"action" (<= 12 words, imperative, e.g. "Call customer to verify EMI date"),
"reason" (<= 20 words, tie it to a specific triggered rule),
"priority" ("high" | "medium" | "low").

Customer: {customer.get('name', 'N/A')}
Risk Score: {risk_score}/100
Triggered rules:
{rules_text}

Respond with ONLY the JSON array, no prose, no markdown fences."""


def build_assistant_prompt(customer: Dict[str, Any], triggered_rules: List[Dict[str, Any]],
                            risk_score: int, history: List[Dict[str, str]], question: str) -> str:
    rules_text = "\n".join(
        f"- {r['rule']}: +{r['points']} ({r['detail']})" for r in triggered_rules
    ) or "- none triggered"

    convo = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-6:])

    return f"""You are an AI assistant inside a bank fraud dashboard, answering a
Credit/Fraud Officer's follow-up questions about ONE specific customer's risk
profile. Only use the facts given below — if asked something not covered by
this data, say plainly that the data isn't available rather than guessing.

Customer profile:
- Name: {customer.get('name', 'N/A')}
- Branch: {customer.get('branch', 'N/A')}
- Loan amount: {customer.get('loan_amount', 'N/A')}
- Risk score: {risk_score}/100
- Triggered rules:
{rules_text}

Conversation so far:
{convo if convo else '(no prior turns)'}

Officer's new question: {question}

Answer in 2-4 sentences, professional tone, no markdown."""


def build_emi_pattern_prompt(payment_dates: List[str], due_day: int) -> str:
    dates_text = ", ".join(payment_dates) if payment_dates else "(no payment history)"
    return f"""Analyze this customer's EMI payment dates against their due day of the
month (day {due_day}). Payment dates recorded: {dates_text}.

Return ONLY a JSON object with:
"pattern" ("consistent_late" | "consistent_on_time" | "irregular" | "insufficient_data"),
"avg_days_late" (integer, 0 if on-time or negative if early),
"suggested_new_due_day" (integer 1-28, or null if no change needed),
"note" (<=25 words explaining the suggestion)."""


def build_withdrawal_pattern_prompt(withdrawals: List[Dict[str, Any]], disbursement_amount: float) -> str:
    wd_text = "\n".join(
        f"- {w['date']}: withdrew {w['amount']} ({w['days_after_disbursement']} days after disbursement)"
        for w in withdrawals
    ) or "- no withdrawals recorded"

    return f"""A loan of amount {disbursement_amount} was disbursed to this customer.
Withdrawal activity since disbursement:
{wd_text}

Return ONLY a JSON object with:
"pattern" ("full_withdrawal_immediate" | "consistent_partial_withdrawal" | "normal_usage" | "insufficient_data"),
"total_withdrawn_pct" (0-100, percent of disbursement withdrawn so far),
"is_red_flag" (true/false),
"note" (<=25 words, factual, for a credit officer report)."""
