import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[str] = "credit_officer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Customer ----------
class CustomerCreate(BaseModel):
    customer_code: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    branch: Optional[str] = "Main Branch"
    kyc_verified: Optional[bool] = True
    gst_number: Optional[str] = None


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    branch: Optional[str] = None
    kyc_verified: Optional[bool] = None
    gst_number: Optional[str] = None


class CustomerOut(BaseModel):
    id: int
    customer_code: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    branch: str
    kyc_verified: bool
    gst_number: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------- Loan ----------
class LoanCreate(BaseModel):
    customer_id: int
    loan_amount: float
    loan_type: Optional[str] = "Personal Loan"
    emi_amount: Optional[float] = 0.0
    emi_due_date: Optional[int] = 5
    tenure_months: Optional[int] = 12
    emi_bounce_count: Optional[int] = 0
    delayed_repayment_count: Optional[int] = 0
    loan_enquiry_count_last_30_days: Optional[int] = 0


class LoanOut(BaseModel):
    id: int
    customer_id: int
    loan_amount: float
    loan_type: str
    emi_amount: float
    emi_due_date: int
    tenure_months: int
    emi_bounce_count: int
    delayed_repayment_count: int
    loan_enquiry_count_last_30_days: int
    status: str
    disbursement_date: datetime.datetime

    class Config:
        from_attributes = True


# ---------- Transaction ----------
class TransactionCreate(BaseModel):
    customer_id: int
    loan_id: Optional[int] = None
    txn_type: str  # credit / debit / cash_withdrawal
    amount: float
    balance_after: Optional[float] = 0.0
    beneficiary: Optional[str] = None
    beneficiary_flagged: Optional[bool] = False
    gst_declared_turnover: Optional[float] = None
    is_cash_withdrawal_post_disbursement: Optional[bool] = False


class TransactionOut(BaseModel):
    id: int
    customer_id: int
    loan_id: Optional[int]
    txn_type: str
    amount: float
    balance_after: float
    beneficiary: Optional[str]
    beneficiary_flagged: bool
    txn_date: datetime.datetime
    is_cash_withdrawal_post_disbursement: bool

    class Config:
        from_attributes = True


# ---------- Fraud ----------
class FraudCheckLoanRequest(BaseModel):
    customer_id: int
    loan_id: int


class FraudCheckTransactionRequest(BaseModel):
    customer_id: int
    transaction_id: int


class FraudScoreRequest(BaseModel):
    customer_id: int


class FraudReportOut(BaseModel):
    id: int
    customer_id: int
    risk_score: int
    risk_level: str
    triggered_rules: str
    ai_explanation: Optional[str]
    recommended_actions: Optional[str]
    generated_at: datetime.datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    customer_id: int
    title: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True
