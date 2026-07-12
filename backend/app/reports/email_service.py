"""
Real-time email alerts for high/critical risk events.

Uses plain smtplib (works with Gmail App Passwords, SendGrid SMTP relay,
Mailtrap for demo/testing, etc.) — no paid API dependency required for a
hackathon submission.

Demo-safety: if SMTP env vars are not set, or the send fails (no internet in
sandbox, wrong creds, etc.), this NEVER raises up to the API layer. It logs
the failure and returns a structured result so the caller/router can still
respond 200 with `"sent": false` instead of crashing the request.
"""

import os
import ssl
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, Dict, Any

logger = logging.getLogger("reports.email_service")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_TIMEOUT_SECONDS = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))

SEVERITY_LABELS = {
    "critical": "🔴 CRITICAL",
    "high": "🟠 HIGH",
    "medium": "🟡 MEDIUM",
    "low": "🟢 LOW",
}


def _is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)


def _build_message(to_email: str, customer_name: str, severity: str, message: str,
                    risk_score: int, pdf_bytes: Optional[bytes] = None,
                    pdf_filename: str = "fraud_report.pdf") -> EmailMessage:
    label = SEVERITY_LABELS.get(severity.lower(), severity.upper())
    msg = EmailMessage()
    msg["Subject"] = f"[{label}] Fraud Alert — {customer_name} (Score: {risk_score}/100)"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    body = (
        f"Fraud Early-Warning System Alert\n"
        f"{'=' * 40}\n\n"
        f"Customer: {customer_name}\n"
        f"Severity: {label}\n"
        f"Risk Score: {risk_score}/100\n\n"
        f"Details:\n{message}\n\n"
        f"Please review this account in the Fraud Dashboard.\n"
        f"{'—' * 40}\n"
        f"This is an automated alert from the Fraud Early-Warning System."
    )
    msg.set_content(body)

    if pdf_bytes:
        msg.add_attachment(
            pdf_bytes, maintype="application", subtype="pdf", filename=pdf_filename,
        )
    return msg


def send_alert_email(
    to_email: str,
    customer_name: str,
    severity: str,
    message: str,
    risk_score: int,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: str = "fraud_report.pdf",
) -> Dict[str, Any]:
    """
    Returns: {"sent": bool, "reason": Optional[str]}
    Never raises.
    """
    if not _is_configured():
        reason = "SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM missing)"
        logger.warning("Email alert skipped — %s", reason)
        return {"sent": False, "reason": reason}

    try:
        email_msg = _build_message(to_email, customer_name, severity, message, risk_score,
                                    pdf_bytes, pdf_filename)
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(email_msg)
        logger.info("Alert email sent to %s for customer=%s severity=%s", to_email, customer_name, severity)
        return {"sent": True, "reason": None}
    except Exception as exc:  # noqa: BLE001 - demo-safety net, never crash the request
        logger.error("Failed to send alert email to %s: %s", to_email, exc)
        return {"sent": False, "reason": str(exc)}
