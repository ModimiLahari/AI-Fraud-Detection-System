"""
Run this once after starting the server to populate demo data:
    python seed_data.py

Creates:
- 1 demo login user (email: officer@bank.com / password: Officer@123)
- 5 customers across branches, with loans & transactions
- Some customers deliberately trigger fraud rules for a good demo
"""
import datetime
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ---- Demo user ----
if not db.query(models.User).filter(models.User.email == "officer@bank.com").first():
    user = models.User(
        full_name="Priya Sharma",
        email="officer@bank.com",
        hashed_password=auth.hash_password("Officer@123"),
        role="credit_officer",
    )
    db.add(user)
    db.commit()
    print("Created demo user: officer@bank.com / Officer@123")

now = datetime.datetime.utcnow()


def make_customer(code, name, branch, kyc=True, gst=None):
    existing = db.query(models.Customer).filter(models.Customer.customer_code == code).first()
    if existing:
        return existing
    c = models.Customer(
        customer_code=code, full_name=name, email=f"{code.lower()}@example.com",
        phone="9876543210", pan_number="ABCDE1234F", aadhaar_number="1234-5678-9012",
        branch=branch, kyc_verified=kyc, gst_number=gst,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---- HIGH RISK customer: EMI bounce + cash withdrawal pattern ----
c1 = make_customer("CUST1001", "Ramesh Kumar", "Hyderabad Branch", kyc=True, gst="GST1001XYZ")
loan1 = models.Loan(
    customer_id=c1.id, loan_amount=500000, loan_type="Business Loan",
    disbursement_date=now - datetime.timedelta(days=60), emi_amount=15000,
    emi_due_date=5, tenure_months=36, emi_bounce_count=3,
    delayed_repayment_count=4, loan_enquiry_count_last_30_days=4,
)
db.add(loan1)
db.commit()
db.refresh(loan1)

txns1 = [
    models.Transaction(customer_id=c1.id, loan_id=loan1.id, txn_type="credit", amount=500000,
                        balance_after=500000, txn_date=now - datetime.timedelta(days=60)),
    models.Transaction(customer_id=c1.id, loan_id=loan1.id, txn_type="cash_withdrawal", amount=480000,
                        balance_after=20000, txn_date=now - datetime.timedelta(days=59),
                        is_cash_withdrawal_post_disbursement=True),
    models.Transaction(customer_id=c1.id, loan_id=loan1.id, txn_type="credit", amount=250000,
                        balance_after=270000, gst_declared_turnover=600000,
                        txn_date=now - datetime.timedelta(days=30)),
]
db.add_all(txns1)

# ---- CRITICAL RISK customer: suspicious beneficiary + repeated cash withdrawal ----
c2 = make_customer("CUST1002", "Sunita Reddy", "Bangalore Branch", kyc=False, gst="GST1002ABC")
loan2 = models.Loan(
    customer_id=c2.id, loan_amount=800000, loan_type="MSME Loan",
    disbursement_date=now - datetime.timedelta(days=45), emi_amount=22000,
    emi_due_date=10, tenure_months=48, emi_bounce_count=5,
    delayed_repayment_count=6, loan_enquiry_count_last_30_days=5,
)
db.add(loan2)
db.commit()
db.refresh(loan2)

txns2 = [
    models.Transaction(customer_id=c2.id, loan_id=loan2.id, txn_type="credit", amount=800000,
                        balance_after=800000, txn_date=now - datetime.timedelta(days=45)),
    models.Transaction(customer_id=c2.id, loan_id=loan2.id, txn_type="cash_withdrawal", amount=750000,
                        balance_after=50000, txn_date=now - datetime.timedelta(days=44),
                        is_cash_withdrawal_post_disbursement=True),
    models.Transaction(customer_id=c2.id, loan_id=loan2.id, txn_type="debit", amount=300000,
                        balance_after=250000, beneficiary="Unknown Shell Traders",
                        beneficiary_flagged=True, txn_date=now - datetime.timedelta(days=20),
                        is_cash_withdrawal_post_disbursement=True),
]
db.add_all(txns2)

# ---- LOW RISK customer: clean record ----
c3 = make_customer("CUST1003", "Arjun Mehta", "Mumbai Branch", kyc=True, gst="GST1003DEF")
loan3 = models.Loan(
    customer_id=c3.id, loan_amount=200000, loan_type="Personal Loan",
    disbursement_date=now - datetime.timedelta(days=90), emi_amount=8000,
    emi_due_date=1, tenure_months=24, emi_bounce_count=0,
    delayed_repayment_count=0, loan_enquiry_count_last_30_days=0,
)
db.add(loan3)
db.commit()
db.refresh(loan3)

txns3 = [
    models.Transaction(customer_id=c3.id, loan_id=loan3.id, txn_type="credit", amount=200000,
                        balance_after=250000, txn_date=now - datetime.timedelta(days=90)),
    models.Transaction(customer_id=c3.id, loan_id=loan3.id, txn_type="debit", amount=8000,
                        balance_after=242000, txn_date=now - datetime.timedelta(days=60)),
]
db.add_all(txns3)

# ---- MEDIUM RISK customer ----
c4 = make_customer("CUST1004", "Kavya Nair", "Chennai Branch", kyc=True, gst="GST1004GHI")
loan4 = models.Loan(
    customer_id=c4.id, loan_amount=350000, loan_type="Vehicle Loan",
    disbursement_date=now - datetime.timedelta(days=120), emi_amount=12000,
    emi_due_date=15, tenure_months=36, emi_bounce_count=3,
    delayed_repayment_count=2, loan_enquiry_count_last_30_days=1,
)
db.add(loan4)
db.commit()

# ---- Another low/medium customer for branch diversity ----
c5 = make_customer("CUST1005", "Vikram Singh", "Delhi Branch", kyc=True, gst="GST1005JKL")
loan5 = models.Loan(
    customer_id=c5.id, loan_amount=150000, loan_type="Personal Loan",
    disbursement_date=now - datetime.timedelta(days=15), emi_amount=6000,
    emi_due_date=20, tenure_months=24, emi_bounce_count=1,
    delayed_repayment_count=0, loan_enquiry_count_last_30_days=0,
)
db.add(loan5)
db.commit()

# ---- Vijayawada Branch: MEDIUM risk (EMI stress, no cash diversion) ----
c6 = make_customer("CUST1006", "Lakshmi Prasanna", "Vijayawada Branch", kyc=True, gst="GST1006VJA")
loan6 = models.Loan(
    customer_id=c6.id, loan_amount=275000, loan_type="Business Loan",
    disbursement_date=now - datetime.timedelta(days=75), emi_amount=9500,
    emi_due_date=8, tenure_months=30, emi_bounce_count=3,
    delayed_repayment_count=2, loan_enquiry_count_last_30_days=2,
)
db.add(loan6)
db.commit()
db.refresh(loan6)

txns6 = [
    models.Transaction(customer_id=c6.id, loan_id=loan6.id, txn_type="credit", amount=275000,
                        balance_after=275000, txn_date=now - datetime.timedelta(days=75)),
    models.Transaction(customer_id=c6.id, loan_id=loan6.id, txn_type="debit", amount=9500,
                        balance_after=265500, txn_date=now - datetime.timedelta(days=45)),
]
db.add_all(txns6)

# ---- Visakhapatnam Branch: CRITICAL risk (GST mismatch + flagged beneficiary) ----
c7 = make_customer("CUST1007", "Ravi Teja Varma", "Visakhapatnam Branch", kyc=False, gst="GST1007VZG")
loan7 = models.Loan(
    customer_id=c7.id, loan_amount=650000, loan_type="MSME Loan",
    disbursement_date=now - datetime.timedelta(days=50), emi_amount=18000,
    emi_due_date=12, tenure_months=42, emi_bounce_count=4,
    delayed_repayment_count=5, loan_enquiry_count_last_30_days=4,
)
db.add(loan7)
db.commit()
db.refresh(loan7)

txns7 = [
    models.Transaction(customer_id=c7.id, loan_id=loan7.id, txn_type="credit", amount=650000,
                        balance_after=650000, txn_date=now - datetime.timedelta(days=50)),
    models.Transaction(customer_id=c7.id, loan_id=loan7.id, txn_type="credit", amount=180000,
                        balance_after=800000, gst_declared_turnover=500000,
                        txn_date=now - datetime.timedelta(days=25)),
    models.Transaction(customer_id=c7.id, loan_id=loan7.id, txn_type="debit", amount=400000,
                        balance_after=400000, beneficiary="Coastal Traders Pvt Ltd",
                        beneficiary_flagged=True, txn_date=now - datetime.timedelta(days=18),
                        is_cash_withdrawal_post_disbursement=True),
]
db.add_all(txns7)

# ---- Warangal Branch: LOW risk (clean record) ----
c8 = make_customer("CUST1008", "Srinivas Rao Konda", "Warangal Branch", kyc=True, gst="GST1008WGL")
loan8 = models.Loan(
    customer_id=c8.id, loan_amount=180000, loan_type="Vehicle Loan",
    disbursement_date=now - datetime.timedelta(days=100), emi_amount=6500,
    emi_due_date=3, tenure_months=24, emi_bounce_count=0,
    delayed_repayment_count=0, loan_enquiry_count_last_30_days=0,
)
db.add(loan8)
db.commit()
db.refresh(loan8)

txns8 = [
    models.Transaction(customer_id=c8.id, loan_id=loan8.id, txn_type="credit", amount=180000,
                        balance_after=195000, txn_date=now - datetime.timedelta(days=100)),
    models.Transaction(customer_id=c8.id, loan_id=loan8.id, txn_type="debit", amount=6500,
                        balance_after=188500, txn_date=now - datetime.timedelta(days=70)),
]
db.add_all(txns8)

db.commit()
db.close()

print("Seed data created successfully!")
print("Login with: officer@bank.com / Officer@123")
print("Now call POST /fraud/generate-score for customer_id 1-8 to generate risk reports.")
