from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import calendar

from database import get_db
from models import User, FixedPayment
from schemas import (
    FixedPayment as FixedPaymentSchema,
    FixedPaymentCreate,
    FixedPaymentUpdate,
    FixedPaymentWithStatus
)
from auth import get_current_user

router = APIRouter()

def calculate_next_due_date(due_day: int) -> datetime:
    now = datetime.now()
    year = now.year
    month = now.month
    
    # Ajustar el día si es mayor que los días del mes actual
    max_day = calendar.monthrange(year, month)[1]
    actual_due_day = min(due_day, max_day)
    
    try:
        next_due = datetime(year, month, actual_due_day)
        
        # Si ya pasó este mes, ir al siguiente
        if next_due <= now:
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
            
            max_day = calendar.monthrange(year, month)[1]
            actual_due_day = min(due_day, max_day)
            next_due = datetime(year, month, actual_due_day)
        
        return next_due
    except ValueError:
        # Manejar casos edge como 31 de febrero
        return datetime(year, month, max_day)

def get_payment_status(payment: FixedPayment, days_until_due: int) -> str:
    if not payment.is_active:
        return "inactive"
    elif days_until_due < 0:
        return "overdue"
    elif days_until_due == 0:
        return "due"
    elif days_until_due <= 2:
        return "warning"
    else:
        return "upcoming"

@router.get("/", response_model=List[FixedPaymentWithStatus])
async def get_fixed_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payments = db.query(FixedPayment).filter(
        FixedPayment.user_id == current_user.id
    ).all()
    
    result = []
    for payment in payments:
        next_due = calculate_next_due_date(payment.due_day)
        days_until_due = (next_due.date() - datetime.now().date()).days
        status = get_payment_status(payment, days_until_due)
        
        payment_with_status = FixedPaymentWithStatus(
            **payment.__dict__,
            next_due=next_due,
            days_until_due=days_until_due,
            status=status
        )
        result.append(payment_with_status)
    
    return result

@router.post("/", response_model=FixedPaymentSchema)
async def create_fixed_payment(
    payment: FixedPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_payment = FixedPayment(
        **payment.dict(),
        user_id=current_user.id
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.put("/{payment_id}", response_model=FixedPaymentSchema)
async def update_fixed_payment(
    payment_id: int,
    payment_update: FixedPaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payment = db.query(FixedPayment).filter(
        FixedPayment.id == payment_id,
        FixedPayment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Pago fijo no encontrado")
    
    # Actualizar campos
    for field, value in payment_update.dict(exclude_unset=True).items():
        setattr(payment, field, value)
    
    db.commit()
    db.refresh(payment)
    return payment

@router.delete("/{payment_id}")
async def delete_fixed_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payment = db.query(FixedPayment).filter(
        FixedPayment.id == payment_id,
        FixedPayment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Pago fijo no encontrado")
    
    db.delete(payment)
    db.commit()
    return {"message": "Pago fijo eliminado exitosamente"}

@router.get("/upcoming")
async def get_upcoming_payments(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payments = db.query(FixedPayment).filter(
        FixedPayment.user_id == current_user.id,
        FixedPayment.is_active == True
    ).all()
    
    upcoming = []
    for payment in payments:
        next_due = calculate_next_due_date(payment.due_day)
        days_until_due = (next_due.date() - datetime.now().date()).days
        
        if 0 <= days_until_due <= days:
            upcoming.append({
                "payment": payment,
                "next_due": next_due,
                "days_until_due": days_until_due
            })
    
    return upcoming
