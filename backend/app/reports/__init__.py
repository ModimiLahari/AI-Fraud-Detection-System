"""
Reports & Alerts Layer.

Exposes:
- pdf_generator.build_customer_pdf(...)   -> one-click PDF fraud report (bytes)
- excel_generator.build_portfolio_excel(...) -> portfolio-wide Excel export (bytes)
- email_service.send_alert_email(...)     -> real-time email alerts, SMTP-based
"""
