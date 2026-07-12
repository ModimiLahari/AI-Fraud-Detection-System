import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """Bank officer / admin login."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), default="credit_officer")  # admin / credit_officer / risk_officer
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
    kyc_verified = Column(Boolean, default=True)
    gst_number = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    loans = relationship("Loan", back_populates="customer", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    fraud_reports = relationship("FraudReport", back_populates="customer", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="customer", cascade="all, delete-orphan")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    loan_amount = Column(Float, nullable=False)
    loan_type = Column(String(50), default="Personal Loan")
    disbursement_date = Column(DateTime, default=datetime.datetime.utcnow)
    emi_amount = Column(Float, default=0.0)
    emi_due_date = Column(Integer, default=5)  # day of month
    tenure_months = Column(Integer, default=12)
    emi_bounce_count = Column(Integer, default=0)
    delayed_repayment_count = Column(Integer, default=0)
    loan_enquiry_count_last_30_days = Column(Integer, default=0)
    status = Column(String(30), default="Active")  # Active / Closed / Defaulted

    customer = relationship("Customer", back_populates="loans")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    txn_type = Column(String(30))  # credit / debit / cash_withdrawal
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, default=0.0)
    beneficiary = Column(String(120), nullable=True)
    beneficiary_flagged = Column(Boolean, default=False)
    gst_declared_turnover = Column(Float, nullable=True)
    txn_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_cash_withdrawal_post_disbursement = Column(Boolean, default=False)

    customer = relationship("Customer", back_populates="transactions")


class FraudReport(Base):
    __tablename__ = "fraud_reports"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="Low")  # Low / Medium / High / Critical
    triggered_rules = Column(Text)  # JSON string list of rule reasons
    ai_explanation = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="fraud_reports")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    title = Column(String(200))
    message = Column(Text)
    severity = Column(String(20), default="Medium")  # Low / Medium / High / Critical
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="alerts")
