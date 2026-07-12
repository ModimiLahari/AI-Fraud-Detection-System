# Bank Fraud Detection & Early Warning System — Backend

FastAPI backend for the **Early Warning for Existing Loan Accounts** hackathon track.
Detects EMI bounce patterns, cash withdrawal after disbursement, fund diversion,
GST turnover mismatch, KYC issues, and suspicious beneficiaries — with AI-generated
plain-English explanations for credit officers.

## Tech Stack
- **FastAPI** + **SQLAlchemy** (SQLite by default, swap to PostgreSQL via `DATABASE_URL`)
- **JWT** authentication (python-jose + passlib/bcrypt)
- **Google Gemini API** for AI risk explanations (with automatic offline fallback)
- **ReportLab** for PDF reports, **openpyxl** for Excel export

## Folder Structure
```
fraud-backend/
├── app/
│   ├── main.py            # FastAPI app + router registration
│   ├── config.py          # Env-based settings
│   ├── database.py        # SQLAlchemy engine/session
│   ├── models.py          # ORM models: User, Customer, Loan, Transaction, FraudReport, Alert
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── auth.py             # JWT + password hashing
│   ├── fraud_engine.py    # Rule-based scoring engine
│   ├── ai_explain.py      # Gemini AI explanation layer
│   ├── reports.py         # PDF / Excel generation
│   └── routers/
│       ├── auth.py
│       ├── customer.py
│       ├── loan.py
│       ├── transaction.py
│       └── fraud.py
├── seed_data.py           # Demo data generator
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd fraud-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in SECRET_KEY / GEMINI_API_KEY
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000** — Swagger docs at **http://localhost:8000/docs**.

### Load demo data (recommended for judges' demo)
```bash
python seed_data.py
```
This creates 8 customers (High/Critical/Medium/Low risk mix across 8 branches — Hyderabad,
Bangalore, Mumbai, Chennai, Delhi, Vijayawada, Visakhapatnam, Warangal) and a login:
- **Email:** officer@bank.com
- **Password:** Officer@123

Then in Swagger, login → copy token → call `POST /fraud/generate-score` for `customer_id` 1–8
to generate fraud reports for each.

## Fraud Scoring Rules

| Rule | Points |
|---|---|
| KYC mismatch | +20 |
| Document mismatch | +25 |
| EMI bounce count > 2 | +15 |
| Sudden high-value transaction | +15 |
| Cash withdrawal after disbursement (one-time) | +20 |
| Cash withdrawal after disbursement (repeated pattern) | +30 |
| GST turnover vs bank credit mismatch (>30%) | +20 |
| Multiple loan enquiries (last 30 days) | +10 |
| Suspicious/flagged beneficiary | +15 |

Score bands: **0–19 Low · 20–44 Medium · 45–69 High · 70–100 Critical**

## Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create officer login |
| POST | `/auth/login` | Get JWT token |
| POST | `/customer/create` | Create customer |
| GET | `/customer/list` | List all customers |
| POST | `/loan/create` | Create loan |
| POST | `/transaction/create` | Create transaction |
| POST | `/fraud/check-loan-application` | Score a loan application |
| POST | `/fraud/check-transaction` | Score a transaction event |
| POST | `/fraud/generate-score` | Full risk re-evaluation for a customer |
| GET | `/fraud/report/{customer_id}` | Latest fraud report |
| GET | `/fraud/report/{customer_id}/history` | Risk score trend over time |
| GET | `/fraud/reasons/{customer_id}` | Triggered rules + AI explanation |
| GET | `/fraud/alerts` | Real-time alert feed |
| GET | `/fraud/dashboard-summary` | Aggregated stats for charts |
| POST | `/fraud/ai-assistant/{customer_id}` | "Why is this customer high risk?" Q&A |
| GET | `/fraud/report/{customer_id}/pdf` | One-click PDF report download |
| GET | `/fraud/report/excel/all` | Excel export — all customers |

All endpoints except `/auth/register` and `/auth/login` require:
`Authorization: Bearer <token>`

## Bonus modules (mounted in addition to the core `/fraud/*` endpoints above)
- **`/ai/*`** — richer, standalone AI endpoints (`explain`, `recommend`, `assistant`, `emi-pattern`, `withdrawal-pattern`), each returning a `source: "gemini" | "offline"` field.
- **`/reports/*`** — alternate PDF/Excel generators plus `POST /reports/email-alert` for SMTP alert delivery (no-ops safely if SMTP env vars aren't set).

These are independent of the `/fraud/report/.../pdf` and `/fraud/report/excel/all` endpoints the frontend uses by default; both are available if you want to compare or swap them in.

## Environment variables
See `.env.example`. Notably `CORS_ORIGINS` (comma-separated list, defaults to `*` for local dev — set it to your deployed frontend URL in production) and the optional `SMTP_*` vars used by `/reports/email-alert`.

## Deployment (Render)
1. Push this folder to GitHub.
2. On Render: New → Web Service → connect repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars from `.env.example` (use PostgreSQL `DATABASE_URL` from a Render Postgres instance for production).
