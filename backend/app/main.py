from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, customer, loan, transaction, fraud
from app.ai.router import router as ai_router
from app.reports.router import router as reports_router

Base.metadata.create_all(bind=engine)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
_allow_credentials = "*" not in _cors_origins  # browsers reject wildcard origin + credentials

app = FastAPI(
    title="Bank Fraud Detection & Early Warning System",
    description=(
        "AI-powered fraud detection and early-warning system for existing loan accounts. "
        "Detects EMI bounce patterns, cash withdrawal after disbursement, fund diversion, "
        "GST mismatch, and other risk signals — with AI-generated explanations."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,  # set CORS_ORIGINS env var in production, e.g. your Vercel domain
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routers (customer, loan, transaction, fraud scoring, auth)
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(loan.router)
app.include_router(transaction.router)
app.include_router(fraud.router)

# Extra AI + Reports modules (advanced /ai/* and /reports/* endpoints)
app.include_router(ai_router)
app.include_router(reports_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "service": "Bank Fraud Detection & Early Warning System",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
