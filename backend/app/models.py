"""
Database models — Phase 1 revision.

Key changes from original v1:
  Customer : added segment, gst_annual_turnover, gst_assessment_period_months,
             gst_scheme, kyc_status (replaces kyc_verified bool),
             bureau_enquiry_count_30d/60d/90d
  Loan     : added loan_purpose, months_active; removed emi_bounce_count,
             delayed_repayment_count, loan_enquiry_count_last_30_days
             (all replaced by structured EmiPaymentEvent / BureauEnquiry tables)
  Transaction: added txn_category, balance_before, beneficiary_account_age_days,
               is_related_party, related_party_name;
               removed gst_declared_turnover (moved to Customer)
  NEW      : EmiPaymentEvent, BureauEnquiry, RuleAuditTrail
  FraudReport: added pillar raw/capped columns
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Text, Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ---------------------------------------------------------------------------
# String constants (used as column values; validated at application layer)
# ---------------------------------------------------------------------------
# Customer.segment       : Salaried | MSME | Self-employed | Merchant | Unknown
# Customer.gst_scheme    : regular | composition | exempt | none
# Customer.kyc_status    : pending | verified | mismatch | fraud
# Transaction.txn_category:
#   salary | loan_disbursement | inter_account_transfer | capital_introduction |
#   refund | reversal | asset_sale | vendor_payment | cash_withdrawal |
#   emi_repayment | related_party | institutional | agricultural_purchase | other
# EmiPaymentEvent.status : paid_on_time | paid_late | bounced | cured | overdue


NON_OPERATING_TXN_CATEGORIES = {
    "loan_disbursement",
    "inter_account_transfer",
    "capital_introduction",
    "refund",
    "reversal",
    "asset_sale",
    "emi_repayment",
    "institutional",
}
"""Categories excluded when computing 'operating bank credits' for GST
reconciliation and transaction-anomaly baselines."""


class User(Base):
    """Bank officer / admin login."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), default="credit_officer")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(30), unique=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120))
    phone = Column(String(20))
    pan_number = Column(String(20))
    aadhaar_number = Column(String(20))
    branch = Column(String(80), default="Main Branch")

    # -- KYC (split from single bool) ----------------------------------------
    # pending  : documents collected, verification in progress (0 pts, Watch)
    # verified : KYC complete and clean (0 pts)
    # mismatch : submitted docs do not match bank/bureau records  → KYC_001
    # fraud    : confirmed / strongly indicated identity fraud    → IDENTITY_FRAUD
    kyc_status = Column(String(20), default="verified")

    # -- GST (moved from Transaction; covers the whole customer) --------------
    gst_number = Column(String(30), nullable=True)
    # Declared outward supply (GSTR-1 total) for the assessment window
    gst_annual_turnover = Column(Float, nullable=True)
    # How many months the above figure covers (used to pro-rate comparison)
    gst_assessment_period_months = Column(Integer, nullable=True)
    # regular | composition | exempt | none
    gst_scheme = Column(String(20), nullable=True)

    # -- Segment --------------------------------------------------------------
    # Salaried | MSME | Self-employed | Merchant | Unknown
    segment = Column(String(30), default="Unknown")

    # -- Bureau enquiry counts (customer-level, not loan-level) ---------------
    bureau_enquiry_count_30d = Column(Integer, default=0)
    bureau_enquiry_count_60d = Column(Integer, default=0)
    bureau_enquiry_count_90d = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # -- Relationships --------------------------------------------------------
    loans = relationship(
        "Loan", back_populates="customer", cascade="all, delete-orphan")
    transactions = relationship(
        "Transaction", back_populates="customer", cascade="all, delete-orphan")
    fraud_reports = relationship(
        "FraudReport", back_populates="customer", cascade="all, delete-orphan")
    alerts = relationship(
        "Alert", back_populates="customer", cascade="all, delete-orphan")
    emi_events = relationship(
        "EmiPaymentEvent", back_populates="customer",
        cascade="all, delete-orphan")
    bureau_enquiries = relationship(
        "BureauEnquiry", back_populates="customer",
        cascade="all, delete-orphan")

    # Backward-compat property (old code that read kyc_verified still works)
    @property
    def kyc_verified(self) -> bool:
        return self.kyc_status == "verified"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    loan_amount = Column(Float, nullable=False)
    loan_type = Column(String(50), default="Personal Loan")
    # Stated purpose at sanction (used for related-party / end-use checks)
    loan_purpose = Column(String(200), nullable=True)
    disbursement_date = Column(DateTime, default=datetime.datetime.utcnow)
    emi_amount = Column(Float, default=0.0)
    emi_due_date = Column(Integer, default=5)     # calendar day 1-28
    tenure_months = Column(Integer, default=12)   # sanctioned tenure
    # months_active: months since first disbursement (stored explicitly;
    # derive as ceil((now - disbursement_date).days / 30) if not set)
    months_active = Column(Integer, default=0)
    status = Column(String(30), default="Active")  # Active|Closed|Defaulted|NPA

    # REMOVED: emi_bounce_count, delayed_repayment_count,
    #          loan_enquiry_count_last_30_days
    # → replaced by EmiPaymentEvent and BureauEnquiry tables

    customer = relationship("Customer", back_populates="loans")
    emi_events = relationship(
        "EmiPaymentEvent", back_populates="loan", cascade="all, delete-orphan")


class EmiPaymentEvent(Base):
    """
    One row per EMI presentation / payment event.

    Replaces the old scalar fields:
        Loan.emi_bounce_count, Loan.delayed_repayment_count

    Enables:
        EMI_B_001  bounce frequency  : count bounced rows / months_active
        EMI_B_002  consecutive bounces: check due_date month sequences
        EMI_D_001  DPD calculation   : dpd_at_payment value
        EMI_B_001  cure analysis     : is_technical_bounce flag
        EMI_LB_001 low-balance check : balance_2d_before_due
    """
    __tablename__ = "emi_payment_events"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    loan_id = Column(Integer, ForeignKey("loans.id"))

    # Scheduled due date for this EMI
    due_date = Column(DateTime, nullable=False)

    # paid_on_time | paid_late | bounced | cured | overdue
    status = Column(String(20), nullable=False)

    # Actual date payment was received (null if still unpaid/overdue)
    paid_date = Column(DateTime, nullable=True)

    # Date bounce was cured (paid after initial bounce); null if not yet cured
    cure_date = Column(DateTime, nullable=True)

    # Days past due at the time of (eventual) payment; 0 = on time
    dpd_at_payment = Column(Integer, default=0)

    # Balance in the account approximately 2 days before due_date.
    # Source: Transaction.balance_after of the nearest preceding transaction
    # in that window.  NULL when no transaction found in the window.
    # NOTE: this is an APPROXIMATION — daily balance snapshots are not
    # available in this schema.  EMI_LB_001 treats it as approximate and
    # declares data_quality="partial" accordingly.
    balance_2d_before_due = Column(Float, nullable=True)

    # True when bounce was presented again and cured on the same calendar day
    # (technical / system failure; excluded from fraud scoring)
    is_technical_bounce = Column(Boolean, default=False)

    emi_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="emi_events")
    loan = relationship("Loan", back_populates="emi_events")


class BureauEnquiry(Base):
    """
    Individual bureau enquiry records — customer-level, not loan-level.
    Used by rule ENQ_M_001.
    """
    __tablename__ = "bureau_enquiries"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    enquiry_date = Column(DateTime, nullable=False)
    enquiry_purpose = Column(String(100), nullable=True)   # e.g. "Home Loan"
    enquiring_institution = Column(String(120), nullable=True)
    # True when this enquiry is part of a 14-day rate-shopping cluster for the
    # same loan type → suppresses false-positive in ENQ_M_001
    is_rate_shopping = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="bureau_enquiries")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)

    # credit | debit | cash_withdrawal
    txn_type = Column(String(30))

    # Structured category — drives exclusion logic in GST_M_001 & TXN_S_001
    # See NON_OPERATING_TXN_CATEGORIES for the exclusion set
    txn_category = Column(String(50), default="other")

    amount = Column(Float, nullable=False)

    # balance_before: balance BEFORE this transaction.
    # More accurate than balance_after for low-balance pre-EMI checks.
    # NULL for legacy records; fallback: balance_after ± amount.
    balance_before = Column(Float, nullable=True)

    # balance_after: balance AFTER this transaction (present in v1)
    balance_after = Column(Float, default=0.0)

    beneficiary = Column(String(120), nullable=True)
    beneficiary_flagged = Column(Boolean, default=False)
    # Age of beneficiary account at transaction time (days); -1 = unknown
    beneficiary_account_age_days = Column(Integer, default=-1)

    # Related-party fields (used by Phase 3 rule REL_P_001)
    is_related_party = Column(Boolean, default=False)
    related_party_name = Column(String(120), nullable=True)

    # Set True when this is a cash withdrawal occurring after loan disbursement
    is_cash_withdrawal_post_disbursement = Column(Boolean, default=False)

    txn_date = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="transactions")


class FraudReport(Base):
    __tablename__ = "fraud_reports"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))

    # composite = pillar_repayment_capped
    #           + pillar_cashflow_capped
    #           + pillar_identity_capped   (max 100)
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="Low")  # Low|Medium|High|Critical

    # Raw = sum of all rule points in pillar before cap
    # Capped = min(raw, pillar_cap)  P1=40, P2=35, P3=25
    pillar_repayment_raw = Column(Integer, default=0)
    pillar_repayment_capped = Column(Integer, default=0)
    pillar_cashflow_raw = Column(Integer, default=0)
    pillar_cashflow_capped = Column(Integer, default=0)
    pillar_identity_raw = Column(Integer, default=0)
    pillar_identity_capped = Column(Integer, default=0)

    # JSON list of RuleResult dicts (full structured output per triggered rule)
    triggered_rules = Column(Text)
    ai_explanation = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="fraud_reports")
    audit_trail = relationship(
        "RuleAuditTrail", back_populates="fraud_report",
        cascade="all, delete-orphan")


class RuleAuditTrail(Base):
    """
    One row per rule evaluated per fraud-report run (triggered or not).

    Provides full regulatory traceability:
        what data was used   → input_value
        what was compared    → threshold
        what it contributed  → points_awarded / maximum_points
        pillar state         → pillar_raw_score / pillar_capped_score
        data reliability     → data_quality
        related events       → event_group_id (prevents double-counting)
    """
    __tablename__ = "rule_audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    fraud_report_id = Column(Integer, ForeignKey("fraud_reports.id"))

    rule_code = Column(String(20), nullable=False)   # EMI_B_001, KYC_001 …
    pillar = Column(String(50), nullable=False)

    # JSON dict — actual values fed to this rule
    input_value = Column(Text)
    # Human-readable threshold description
    threshold = Column(String(300))

    points_awarded = Column(Integer, default=0)
    maximum_points = Column(Integer, default=0)   # rule-level cap
    severity = Column(String(20))   # None|Watch|Low|Moderate|High|Critical

    # Pillar state at the moment this rule was evaluated
    pillar_raw_score = Column(Integer, default=0)    # running raw for pillar
    pillar_capped_score = Column(Integer, default=0) # after cap

    reason = Column(Text)
    recommended_action = Column(Text, nullable=True)
    data_source = Column(String(300))  # e.g. "loan_id:1, emi_event_ids:[3,4]"

    # sufficient | partial | insufficient | unavailable
    data_quality = Column(String(20), default="sufficient")

    # JSON list of secondary signals that support (but do not independently
    # score) this rule
    supporting_signals = Column(Text, nullable=True)

    # Groups rules triggered by the same underlying event to prevent
    # double-counting.  When two rules share an event_group_id the engine
    # counts only the primary rule's points.
    event_group_id = Column(String(40), nullable=True)

    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)

    fraud_report = relationship("FraudReport", back_populates="audit_trail")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    title = Column(String(200))
    message = Column(Text)
    severity = Column(String(20), default="Medium")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="alerts")
