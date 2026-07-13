"""
Phase 1 revised seed data.

Changes from original v1:
  - Customer : kyc_status instead of kyc_verified bool
               gst_annual_turnover + gst_assessment_period_months +
               gst_scheme + segment at customer level
               bureau_enquiry_count_30d/60d/90d
  - Loan     : loan_purpose, months_active added
               emi_bounce_count / delayed_repayment_count removed
  - Transaction : txn_category populated on every row
                  gst_declared_turnover removed (moved to Customer)
                  balance_before added
  - New rows : EmiPaymentEvent (replaces scalar counts)
               BureauEnquiry
  - New customers : CUST1009 (round-trip, Phase 3 seed)
                    CUST1010 (chronic delay, Phase 2 seed)

Run once after migrations:
    cd backend
    python seed_data.py

Expected Phase 1 composite scores
----------------------------------
CUST1001  Ramesh Kumar    CASH_D_001 Severe(25) + GST_M_001 High(20) +
                          ENQ Low(4)  → P2 raw 49 capped 35 → composite ~35
CUST1002  Sunita Reddy   IDENTITY_FRAUD(20) + CASH_D_001 Critical(25) +
                          ENQ Mod(8)  → P3=20 P2=33 → composite ~53  High
CUST1003  Arjun Mehta    All rules pass → composite 0  Low
CUST1004  Kavya Nair     ENQ Low(4)  → composite 4  Low
CUST1007  Ravi Teja      KYC_001(12) + GST_M_001 High(20) + ENQ Low(4)
                          → P3=12 P2=24 → composite ~36  High
CUST1009  Pradeep Anand  All Phase-1 rules pass (round-trip = Phase 3)
                          → composite 0  Low
CUST1010  Meena Krishnan All Phase-1 rules pass (chronic delay = Phase 2)
                          → composite 0  Low
"""
import datetime
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ---------------------------------------------------------------------------
# Demo login user
# ---------------------------------------------------------------------------
if not db.query(models.User).filter(
        models.User.email == "officer@bank.com").first():
    db.add(models.User(
        full_name="Priya Sharma",
        email="officer@bank.com",
        hashed_password=auth.hash_password("Officer@123"),
        role="credit_officer",
    ))
    db.commit()
    print("Created demo user: officer@bank.com / Officer@123")

NOW = datetime.datetime.utcnow()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def upsert_customer(
        code, name, branch,
        kyc_status="verified",
        gst=None, gst_turnover=None, gst_months=None, gst_scheme=None,
        segment="Unknown",
        enq_30d=0, enq_60d=0, enq_90d=0):
    c = db.query(models.Customer).filter(
        models.Customer.customer_code == code).first()
    if c:
        return c
    c = models.Customer(
        customer_code=code,
        full_name=name,
        email=f"{code.lower()}@example.com",
        phone="9876543210",
        pan_number="ABCDE1234F",
        aadhaar_number="1234-5678-9012",
        branch=branch,
        kyc_status=kyc_status,
        gst_number=gst,
        gst_annual_turnover=gst_turnover,
        gst_assessment_period_months=gst_months,
        gst_scheme=gst_scheme,
        segment=segment,
        bureau_enquiry_count_30d=enq_30d,
        bureau_enquiry_count_60d=enq_60d,
        bureau_enquiry_count_90d=enq_90d,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def add_loan(customer_id, amount, loan_type,
             months_ago=60, emi=0, emi_due_date=5,
             tenure=36, months_active=2,
             loan_purpose=None, status="Active"):
    loan = models.Loan(
        customer_id=customer_id,
        loan_amount=amount,
        loan_type=loan_type,
        loan_purpose=loan_purpose,
        disbursement_date=NOW - datetime.timedelta(days=months_ago * 30),
        emi_amount=emi,
        emi_due_date=emi_due_date,
        tenure_months=tenure,
        months_active=months_active,
        status=status,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def add_txn(customer_id, loan_id, txn_type, amount, balance_after,
            txn_category="other",
            beneficiary=None, flagged=False,
            days_ago=0, post_disb_cash=False,
            balance_before=None,
            beneficiary_account_age_days=-1,
            is_related_party=False,
            related_party_name=None):
    t = models.Transaction(
        customer_id=customer_id,
        loan_id=loan_id,
        txn_type=txn_type,
        txn_category=txn_category,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        beneficiary=beneficiary,
        beneficiary_flagged=flagged,
        txn_date=NOW - datetime.timedelta(days=days_ago),
        is_cash_withdrawal_post_disbursement=post_disb_cash,
        beneficiary_account_age_days=beneficiary_account_age_days,
        is_related_party=is_related_party,
        related_party_name=related_party_name,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def add_emi_event(customer_id, loan_id, due_days_ago, status,
                  emi_amount, dpd=0,
                  paid_days_ago=None, cure_days_ago=None,
                  balance_2d_before=None, is_technical=False):
    paid_date = (
        NOW - datetime.timedelta(days=paid_days_ago)
        if paid_days_ago is not None else None
    )
    cure_date = (
        NOW - datetime.timedelta(days=cure_days_ago)
        if cure_days_ago is not None else None
    )
    e = models.EmiPaymentEvent(
        customer_id=customer_id,
        loan_id=loan_id,
        due_date=NOW - datetime.timedelta(days=due_days_ago),
        status=status,
        paid_date=paid_date,
        cure_date=cure_date,
        dpd_at_payment=dpd,
        balance_2d_before_due=balance_2d_before,
        emi_amount=emi_amount,
        is_technical_bounce=is_technical,
    )
    db.add(e)
    db.commit()
    return e


def add_bureau_enquiry(customer_id, purpose, days_ago,
                       institution, rate_shopping=False):
    e = models.BureauEnquiry(
        customer_id=customer_id,
        enquiry_date=NOW - datetime.timedelta(days=days_ago),
        enquiry_purpose=purpose,
        enquiring_institution=institution,
        is_rate_shopping=rate_shopping,
    )
    db.add(e)
    db.commit()
    return e


# ===========================================================================
# CUST1001 — HIGH RISK
# Phase 1 rules triggered: CASH_D_001 Severe, GST_M_001 High, ENQ Low
# Phase 2 seed: 3 EMI bounces across 2 consecutive months (EMI_B_001/002)
# ===========================================================================
c1 = upsert_customer(
    "CUST1001", "Ramesh Kumar", "Hyderabad Branch",
    gst="GST1001XYZ",
    gst_turnover=600_000,   # declared ₹6L for 3-month period
    gst_months=3,
    gst_scheme="regular",
    segment="MSME",
    enq_30d=4, enq_60d=4, enq_90d=4,   # ENQ_M_001 Low (4 pts)
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c1.id).first():

    l1 = add_loan(
        c1.id, 500_000, "Business Loan",
        months_ago=2, emi=15_000, emi_due_date=5,
        tenure=36, months_active=2,
        loan_purpose="Working capital for trading business",
    )

    # Disbursement credit — excluded from anomaly + GST comparison
    add_txn(c1.id, l1.id, "credit", 500_000, 500_000,
            txn_category="loan_disbursement", days_ago=60)

    # Cash withdrawal next day — CASH_D_001 Severe (ratio 96%)
    add_txn(c1.id, l1.id, "cash_withdrawal", 480_000, 20_000,
            txn_category="cash_withdrawal",
            balance_before=500_000,
            days_ago=59, post_disb_cash=True)

    # Operating credit (₹2.5L) — GST declared ₹6L, mismatch ~58%
    # → GST_M_001 High (20 pts)
    add_txn(c1.id, l1.id, "credit", 250_000, 270_000,
            txn_category="vendor_payment",
            days_ago=30)

    # Small routine debit to form anomaly baseline
    for d, amt in [(55, 8_000), (50, 9_500), (45, 7_200)]:
        add_txn(c1.id, l1.id, "debit", amt, 260_000,
                txn_category="vendor_payment", days_ago=d)

    # EMI events — 2 bounces in consecutive months (Phase 2 seed)
    add_emi_event(c1.id, l1.id, 60, "bounced", 15_000,
                  dpd=5, cure_days_ago=55, balance_2d_before=3_000)
    add_emi_event(c1.id, l1.id, 30, "bounced", 15_000,
                  dpd=3, cure_days_ago=27, balance_2d_before=1_500)
    add_emi_event(c1.id, l1.id,  5, "paid_late", 15_000,
                  dpd=8, paid_days_ago=0, balance_2d_before=8_000)

    add_bureau_enquiry(c1.id, "Business Loan", 20, "HDFC Bank")
    add_bureau_enquiry(c1.id, "Business Loan", 18, "Axis Bank")
    add_bureau_enquiry(c1.id, "Personal Loan", 15, "ICICI Bank")
    add_bureau_enquiry(c1.id, "Business Loan", 10, "Kotak Bank")


# ===========================================================================
# CUST1002 — CRITICAL RISK
# Phase 1: IDENTITY_FRAUD (20), CASH_D_001 Critical (25), ENQ Moderate (8)
# ===========================================================================
c2 = upsert_customer(
    "CUST1002", "Sunita Reddy", "Bangalore Branch",
    kyc_status="fraud",          # → IDENTITY_FRAUD 20 pts
    gst="GST1002ABC",
    gst_turnover=800_000,
    gst_months=3,
    gst_scheme="regular",
    segment="MSME",
    enq_30d=5, enq_60d=5, enq_90d=6,   # ENQ Moderate (8 pts)
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c2.id).first():

    l2 = add_loan(
        c2.id, 800_000, "MSME Loan",
        months_ago=1, emi=22_000, emi_due_date=10,
        tenure=48, months_active=1,
        loan_purpose="Equipment purchase for manufacturing unit",
    )

    add_txn(c2.id, l2.id, "credit", 800_000, 800_000,
            txn_category="loan_disbursement", days_ago=45)

    # Large cash withdrawal day+1 — ratio 93.75% → CASH_D_001 Critical
    add_txn(c2.id, l2.id, "cash_withdrawal", 750_000, 50_000,
            txn_category="cash_withdrawal",
            balance_before=800_000,
            days_ago=44, post_disb_cash=True)

    # Transfer to flagged beneficiary (new account, 12 days old)
    add_txn(c2.id, l2.id, "debit", 300_000, 250_000,
            txn_category="vendor_payment",
            beneficiary="Unknown Shell Traders",
            flagged=True,
            beneficiary_account_age_days=12,
            days_ago=20)

    # Routine debits for anomaly baseline
    for d, amt in [(40, 15_000), (35, 18_000), (28, 12_000)]:
        add_txn(c2.id, l2.id, "debit", amt, 230_000,
                txn_category="vendor_payment", days_ago=d)

    add_emi_event(c2.id, l2.id, 10, "bounced", 22_000,
                  cure_days_ago=7, balance_2d_before=1_200)

    for day_ago, inst in [
        (25, "SBI"), (22, "PNB"), (20, "HDFC Bank"),
        (18, "Axis"), (15, "Kotak"),
    ]:
        add_bureau_enquiry(c2.id, "Business Loan", day_ago, inst)


# ===========================================================================
# CUST1003 — LOW RISK: clean record
# All Phase 1 rules → 0 pts / not triggered
# ===========================================================================
c3 = upsert_customer(
    "CUST1003", "Arjun Mehta", "Mumbai Branch",
    gst_turnover=None,   # no GST turnover → GST_M_001 suppressed
    segment="Salaried",
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c3.id).first():

    l3 = add_loan(
        c3.id, 200_000, "Personal Loan",
        months_ago=3, emi=8_000, emi_due_date=1,
        tenure=24, months_active=3,
        loan_purpose="Home renovation",
    )

    add_txn(c3.id, l3.id, "credit", 200_000, 250_000,
            txn_category="loan_disbursement", days_ago=90)

    # Regular salary credits — form anomaly baseline
    for d in [85, 55, 25]:
        add_txn(c3.id, l3.id, "credit", 55_000, 240_000,
                txn_category="salary", days_ago=d)

    # EMI debits
    for d in [60, 30]:
        add_txn(c3.id, l3.id, "debit", 8_000, 232_000,
                txn_category="emi_repayment", days_ago=d)

    add_emi_event(c3.id, l3.id, 60, "paid_on_time", 8_000,
                  balance_2d_before=55_000)
    add_emi_event(c3.id, l3.id, 30, "paid_on_time", 8_000,
                  balance_2d_before=48_000)


# ===========================================================================
# CUST1004 — MEDIUM: enquiry stress, no cash diversion
# Phase 1: ENQ Low (4 pts)
# Phase 2 seed: 2 bounces non-consecutive
# ===========================================================================
c4 = upsert_customer(
    "CUST1004", "Kavya Nair", "Chennai Branch",
    gst="GST1004GHI",
    segment="Self-employed",
    enq_30d=3, enq_60d=3, enq_90d=3,
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c4.id).first():

    l4 = add_loan(
        c4.id, 350_000, "Vehicle Loan",
        months_ago=4, emi=12_000, emi_due_date=15,
        tenure=36, months_active=4,
        loan_purpose="Commercial vehicle purchase",
    )

    add_txn(c4.id, l4.id, "credit", 350_000, 380_000,
            txn_category="loan_disbursement", days_ago=120)

    for d, amt in [(110, 9_000), (80, 11_000), (50, 8_500), (20, 10_000)]:
        add_txn(c4.id, l4.id, "debit", amt, 370_000,
                txn_category="vendor_payment", days_ago=d)

    add_emi_event(c4.id, l4.id, 90, "bounced", 12_000,
                  dpd=4, cure_days_ago=86, balance_2d_before=5_000)
    add_emi_event(c4.id, l4.id, 60, "paid_on_time", 12_000,
                  balance_2d_before=18_000)
    add_emi_event(c4.id, l4.id, 30, "bounced", 12_000,
                  dpd=6, cure_days_ago=24, balance_2d_before=2_200)

    add_bureau_enquiry(c4.id, "Personal Loan", 25, "Axis Bank")
    add_bureau_enquiry(c4.id, "Vehicle Loan", 20, "HDFC Bank")
    add_bureau_enquiry(c4.id, "Business Loan", 15, "Kotak Bank")


# ===========================================================================
# CUST1005 — LOW-MEDIUM: single clean EMI, recent loan
# ===========================================================================
c5 = upsert_customer(
    "CUST1005", "Vikram Singh", "Delhi Branch",
    segment="Salaried",
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c5.id).first():

    l5 = add_loan(
        c5.id, 150_000, "Personal Loan",
        months_ago=1, emi=6_000, emi_due_date=20,
        tenure=24, months_active=1,
        loan_purpose="Medical expenses",
    )
    add_txn(c5.id, l5.id, "credit", 150_000, 160_000,
            txn_category="loan_disbursement", days_ago=15)

    for d in [12, 10, 8]:
        add_txn(c5.id, l5.id, "credit", 42_000, 155_000,
                txn_category="salary", days_ago=d)

    add_emi_event(c5.id, l5.id, 5, "paid_on_time", 6_000,
                  balance_2d_before=22_000)


# ===========================================================================
# CUST1006 — MEDIUM: EMI stress, no fund diversion
# ===========================================================================
c6 = upsert_customer(
    "CUST1006", "Lakshmi Prasanna", "Vijayawada Branch",
    gst="GST1006VJA",
    gst_turnover=300_000,
    gst_months=3,
    gst_scheme="regular",
    segment="MSME",
    enq_30d=2, enq_60d=2, enq_90d=2,
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c6.id).first():

    l6 = add_loan(
        c6.id, 275_000, "Business Loan",
        months_ago=3, emi=9_500, emi_due_date=8,
        tenure=30, months_active=3,
        loan_purpose="Shop renovation",
    )
    add_txn(c6.id, l6.id, "credit", 275_000, 275_000,
            txn_category="loan_disbursement", days_ago=75)

    # Operating credits match GST closely — GST_M_001 not triggered
    add_txn(c6.id, l6.id, "credit", 100_000, 350_000,
            txn_category="vendor_payment", days_ago=60)
    add_txn(c6.id, l6.id, "credit", 95_000, 420_000,
            txn_category="vendor_payment", days_ago=30)

    for d, amt in [(70, 12_000), (55, 9_500), (40, 11_000), (25, 10_000)]:
        add_txn(c6.id, l6.id, "debit", amt, 400_000,
                txn_category="vendor_payment", days_ago=d)

    add_emi_event(c6.id, l6.id, 45, "paid_late", 9_500,
                  dpd=5, paid_days_ago=40, balance_2d_before=8_000)
    add_emi_event(c6.id, l6.id, 15, "paid_on_time", 9_500,
                  balance_2d_before=15_000)


# ===========================================================================
# CUST1007 — CRITICAL: KYC mismatch + GST mismatch + flagged beneficiary
# Phase 1: KYC_001 (12), GST_M_001 High (20), ENQ Low (4)
# ===========================================================================
c7 = upsert_customer(
    "CUST1007", "Ravi Teja Varma", "Visakhapatnam Branch",
    kyc_status="mismatch",       # → KYC_001 12 pts
    gst="GST1007VZG",
    gst_turnover=500_000,        # declared ₹5L; operating credit only ₹1.8L
    gst_months=3,
    gst_scheme="regular",
    segment="MSME",
    enq_30d=4, enq_60d=5, enq_90d=5,
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c7.id).first():

    l7 = add_loan(
        c7.id, 650_000, "MSME Loan",
        months_ago=2, emi=18_000, emi_due_date=12,
        tenure=42, months_active=2,
        loan_purpose="Export business expansion",
    )

    add_txn(c7.id, l7.id, "credit", 650_000, 650_000,
            txn_category="loan_disbursement", days_ago=50)

    # Operating credit ₹1.8L — GST ₹5L, mismatch 64%
    add_txn(c7.id, l7.id, "credit", 180_000, 800_000,
            txn_category="vendor_payment", days_ago=25)

    # Routine debits for baseline
    for d, amt in [(48, 8_000), (46, 9_000), (44, 7_500)]:
        add_txn(c7.id, l7.id, "debit", amt, 790_000,
                txn_category="vendor_payment", days_ago=d)

    # Transfer to flagged beneficiary — Phase 2 BEN_F_001 seed
    add_txn(c7.id, l7.id, "debit", 400_000, 400_000,
            txn_category="vendor_payment",
            beneficiary="Coastal Traders Pvt Ltd",
            flagged=True,
            beneficiary_account_age_days=18,
            days_ago=18,
            post_disb_cash=True)

    add_emi_event(c7.id, l7.id, 12, "bounced", 18_000,
                  cure_days_ago=9, balance_2d_before=6_000)

    for d, inst in [(20, "SBI"), (18, "PNB"), (15, "HDFC Bank"), (12, "Axis")]:
        add_bureau_enquiry(c7.id, "MSME Loan", d, inst)


# ===========================================================================
# CUST1008 — LOW RISK: clean Warangal branch
# ===========================================================================
c8 = upsert_customer(
    "CUST1008", "Srinivas Rao Konda", "Warangal Branch",
    segment="Salaried",
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c8.id).first():

    l8 = add_loan(
        c8.id, 180_000, "Vehicle Loan",
        months_ago=4, emi=6_500, emi_due_date=3,
        tenure=24, months_active=4,
        loan_purpose="Two-wheeler purchase",
    )
    add_txn(c8.id, l8.id, "credit", 180_000, 195_000,
            txn_category="loan_disbursement", days_ago=100)

    for d in [95, 65, 35]:
        add_txn(c8.id, l8.id, "credit", 38_000, 185_000,
                txn_category="salary", days_ago=d)

    for d in [70, 40]:
        add_emi_event(c8.id, l8.id, d, "paid_on_time", 6_500,
                      balance_2d_before=30_000)


# ===========================================================================
# CUST1009 — ROUND-TRIP scenario (Phase 3 seed)
# Phase 1 rules: all pass → composite 0
# Phase 3 rule ROUND_001 will score this when implemented
# ===========================================================================
c9 = upsert_customer(
    "CUST1009", "Pradeep Anand", "Hyderabad Branch",
    gst="GST1009HYD",
    gst_turnover=400_000,
    gst_months=3,
    gst_scheme="regular",
    segment="MSME",
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c9.id).first():

    l9 = add_loan(
        c9.id, 300_000, "Business Loan",
        months_ago=1, emi=10_000, emi_due_date=7,
        tenure=36, months_active=1,
        loan_purpose="Working capital",
    )
    add_txn(c9.id, l9.id, "credit", 300_000, 300_000,
            txn_category="loan_disbursement", days_ago=30)

    # Same-day outward to related entity
    add_txn(c9.id, l9.id, "debit", 285_000, 15_000,
            txn_category="vendor_payment",
            beneficiary="Anand Holdings LLP",
            is_related_party=True,
            related_party_name="Pradeep Anand (proprietor)",
            days_ago=30)

    # Return credit 5 days later — round-trip indicator
    add_txn(c9.id, l9.id, "credit", 270_000, 285_000,
            txn_category="other",
            beneficiary="Anand Holdings LLP",
            is_related_party=True,
            related_party_name="Pradeep Anand (proprietor)",
            days_ago=25)

    # Routine operating credits for baseline
    for d, amt in [(20, 18_000), (15, 22_000), (10, 19_000)]:
        add_txn(c9.id, l9.id, "credit", amt, 295_000,
                txn_category="vendor_payment", days_ago=d)

    # Operating credits for GST comparison — ₹4L declared, ~₹1.8L credits
    # mismatch ~55% → would trigger GST_M_001 High — seeded intentionally
    # to show round-trip distorts operating credits
    add_txn(c9.id, l9.id, "credit", 180_000, 465_000,
            txn_category="vendor_payment", days_ago=28)

    add_emi_event(c9.id, l9.id, 5, "paid_on_time", 10_000,
                  balance_2d_before=40_000)


# ===========================================================================
# CUST1010 — CHRONIC DELAY scenario (Phase 2 seed)
# Phase 1 rules: all pass → composite 0
# Phase 2 rule EMI_D_001 will score this when implemented
# ===========================================================================
c10 = upsert_customer(
    "CUST1010", "Meena Krishnan", "Chennai Branch",
    gst="GST1010CHN",
    gst_turnover=250_000,
    gst_months=3,
    gst_scheme="regular",
    segment="Self-employed",
    enq_30d=1, enq_60d=1, enq_90d=2,
)
if not db.query(models.Loan).filter(
        models.Loan.customer_id == c10.id).first():

    l10 = add_loan(
        c10.id, 200_000, "Personal Loan",
        months_ago=6, emi=8_000, emi_due_date=5,
        tenure=24, months_active=6,
        loan_purpose="Medical expenses",
    )
    add_txn(c10.id, l10.id, "credit", 200_000, 200_000,
            txn_category="loan_disbursement", days_ago=180)

    # Operating credits for GST comparison (matches well — rule not triggered)
    add_txn(c10.id, l10.id, "credit", 82_000, 250_000,
            txn_category="vendor_payment", days_ago=90)
    add_txn(c10.id, l10.id, "credit", 79_000, 310_000,
            txn_category="vendor_payment", days_ago=60)

    # Routine debits for anomaly baseline
    for d, amt in [(170, 5_000), (140, 6_500), (110, 4_800),
                   (80, 5_200), (50, 6_000), (20, 5_500)]:
        add_txn(c10.id, l10.id, "debit", amt, 190_000,
                txn_category="vendor_payment", days_ago=d)

    # 6 months of consistently late EMI payments — EMI_D_001 High seed
    emi_schedule = [
        # (due_days_ago, paid_days_ago, dpd, balance_2d_before)
        (150, 143, 7, 3_500),
        (120, 114, 6, 4_200),
        (90,  83,  7, 2_800),
        (60,  52,  8, 3_100),
        (30,  22,  8, 2_500),
        (5,   None, 0, 1_800),   # current month — overdue
    ]
    for due_ago, paid_ago, dpd, bal in emi_schedule:
        status = "paid_late" if paid_ago is not None else "overdue"
        add_emi_event(
            c10.id, l10.id, due_ago, status, 8_000,
            dpd=dpd, paid_days_ago=paid_ago,
            balance_2d_before=bal,
        )


db.commit()
db.close()

print("\nPhase 1 seed data created successfully.")
print("Login: officer@bank.com / Officer@123\n")
print("Expected Phase 1 composite scores (thresholds: Low<20, Medium<45, High<70, Critical>=70):")
print("  CUST1001 Ramesh Kumar   : ~35  Medium  (CASH_D_001 Severe(25) + GST_M_001 High(20) + ENQ Low(4) → P2 capped 35)")
print("  CUST1002 Sunita Reddy   : ~40  Medium  (IDENTITY_FRAUD(20) + CASH_D_001 Critical(25) → P2 capped 25 + P3=20)")
print("  CUST1003 Arjun Mehta    :   0  Low     (all rules pass)")
print("  CUST1004 Kavya Nair     :   4  Low     (ENQ Low(4) only)")
print("  CUST1007 Ravi Teja Varma: ~36  Medium  (KYC_001(12) + GST_M_001 High(20) + ENQ Low(4) → P3=12 P2=24)")
print("  CUST1009 Pradeep Anand  :   0  Low     (round-trip = Phase 3, not yet scored)")
print("  CUST1010 Meena Krishnan :   0  Low     (chronic delay = Phase 2, not yet scored)")
print()
print("NOTE: 'High' label requires score >= 45. CUST1001/1007 score ~35-36 = Medium.")
print("      CUST1002 scores ~40-45 = Medium/boundary depending on P2 cap.")
print("      Source of truth: risk_level_from_score() in fraud_engine.py")
