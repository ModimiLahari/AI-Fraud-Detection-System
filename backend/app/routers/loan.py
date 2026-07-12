from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/loan", tags=["Loan"])


@router.post("/create", response_model=schemas.LoanOut)
def create_loan(
    payload: schemas.LoanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    customer = db.query(models.Customer).filter(models.Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    loan = models.Loan(**payload.model_dump())
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.get("/list", response_model=List[schemas.LoanOut])
def list_loans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Loan).order_by(models.Loan.id).all()


@router.get("/customer/{customer_id}", response_model=List[schemas.LoanOut])
def get_loans_for_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Loan).filter(models.Loan.customer_id == customer_id).all()


@router.put("/{loan_id}", response_model=schemas.LoanOut)
def update_loan(
    loan_id: int,
    payload: schemas.LoanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, field, value)

    db.commit()
    db.refresh(loan)
    return loan


@router.delete("/{loan_id}")
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    db.delete(loan)
    db.commit()
    return {"detail": "Loan deleted"}
