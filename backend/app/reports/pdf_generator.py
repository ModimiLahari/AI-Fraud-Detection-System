"""
Generates a one-click, bank-branded Fraud Risk Report PDF for a single customer.

Uses reportlab (pure Python, no external binaries needed — safe for Render/
Railway free-tier deploys that can't apt-install wkhtmltopdf etc.).

Returns raw PDF bytes so the router can either stream them directly or
save them to disk — caller's choice.
"""

import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger("reports.pdf_generator")

TIER_COLORS = {
    "Low": colors.HexColor("#22C55E"),
    "Medium": colors.HexColor("#EAB308"),
    "High": colors.HexColor("#F59E0B"),
    "Critical": colors.HexColor("#EF4444"),
}
NAVY = colors.HexColor("#0B1220")
SLATE = colors.HexColor("#475569")


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="BankTitle", fontSize=18, leading=22, textColor=NAVY,
                           fontName="Helvetica-Bold", alignment=TA_LEFT))
    ss.add(ParagraphStyle(name="SubTitle", fontSize=10, leading=14, textColor=SLATE,
                           fontName="Helvetica", alignment=TA_LEFT))
    ss.add(ParagraphStyle(name="SectionHeader", fontSize=12, leading=16, textColor=NAVY,
                           fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6))
    ss.add(ParagraphStyle(name="Body", fontSize=10, leading=15, textColor=colors.HexColor("#1E293B")))
    ss.add(ParagraphStyle(name="ScoreBig", fontSize=28, leading=32, fontName="Helvetica-Bold",
                           alignment=TA_CENTER))
    ss.add(ParagraphStyle(name="Footer", fontSize=8, textColor=SLATE, alignment=TA_CENTER))
    return ss


def build_customer_pdf(
    customer: Dict[str, Any],
    risk_score: int,
    triggered_rules: List[Dict[str, Any]],
    ai_explanation: Optional[str] = None,
    recommendations: Optional[List[Dict[str, str]]] = None,
    generated_by: str = "Fraud Early-Warning System",
) -> bytes:
    """
    customer: {"id","name","branch","loan_amount", ...}
    triggered_rules: [{"rule","points","detail"}, ...]
    recommendations: [{"action","reason","priority"}, ...]
    """
    tier = _risk_tier(risk_score)
    tier_color = TIER_COLORS.get(tier, SLATE)
    styles = _styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"Fraud Risk Report - {customer.get('name', 'Customer')}",
    )

    story = []

    # Header
    story.append(Paragraph("Fraud Risk Report", styles["BankTitle"]))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')} · {generated_by}",
        styles["SubTitle"],
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#E2E8F0"), thickness=1))
    story.append(Spacer(1, 10))

    # Customer summary table
    cust_table_data = [
        ["Customer Name", customer.get("name", "N/A")],
        ["Customer ID", str(customer.get("id", "N/A"))],
        ["Branch", customer.get("branch", "N/A")],
        ["Loan Amount", str(customer.get("loan_amount", "N/A"))],
    ]
    cust_table = Table(cust_table_data, colWidths=[45 * mm, 110 * mm])
    cust_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), SLATE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(cust_table)
    story.append(Spacer(1, 14))

    # Risk score block
    score_table = Table(
        [[Paragraph(f"{risk_score}<font size=12>/100</font>", styles["ScoreBig"])],
         [Paragraph(f"{tier.upper()} RISK", ParagraphStyle(
             name="TierLabel", fontSize=11, fontName="Helvetica-Bold",
             alignment=TA_CENTER, textColor=colors.white))]],
        colWidths=[170 * mm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("BACKGROUND", (0, 1), (-1, 1), tier_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 16))

    # Triggered rules
    story.append(Paragraph("Triggered Risk Factors", styles["SectionHeader"]))
    if triggered_rules:
        rows = [["Rule", "Points", "Detail"]]
        for r in sorted(triggered_rules, key=lambda x: x["points"], reverse=True):
            rows.append([r["rule"], f"+{r['points']}", r.get("detail", "")])
        rules_table = Table(rows, colWidths=[45 * mm, 20 * mm, 105 * mm])
        rules_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1220")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rules_table)
    else:
        story.append(Paragraph("No fraud rules triggered for this customer.", styles["Body"]))
    story.append(Spacer(1, 10))

    # AI explanation
    if ai_explanation:
        story.append(Paragraph("AI Risk Explanation", styles["SectionHeader"]))
        story.append(Paragraph(ai_explanation, styles["Body"]))
        story.append(Spacer(1, 10))

    # Recommendations
    if recommendations:
        story.append(Paragraph("Recommended Actions", styles["SectionHeader"]))
        rows = [["Priority", "Action", "Reason"]]
        priority_order = {"high": 0, "medium": 1, "low": 2}
        for rec in sorted(recommendations, key=lambda r: priority_order.get(r.get("priority", "medium"), 1)):
            rows.append([rec.get("priority", "medium").upper(), rec.get("action", ""), rec.get("reason", "")])
        rec_table = Table(rows, colWidths=[22 * mm, 63 * mm, 85 * mm])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1220")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rec_table)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#E2E8F0"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report is system-generated by the Fraud Early-Warning Dashboard for internal "
        "credit/fraud review purposes only.", styles["Footer"],
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    logger.info("Generated PDF report for customer_id=%s (%d bytes)", customer.get("id"), len(pdf_bytes))
    return pdf_bytes
