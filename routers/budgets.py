from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, Budget, Transaction, TransactionType
from schemas import (
    Budget as BudgetSchema,
    BudgetCreate,
    BudgetUpdate,
    BudgetWithSpent
)
from auth import get_current_user

router = APIRouter()

def calculate_budget_status(budget: Budget, spent_amount: float) -> str:
    percentage = (spent_amount / budget.amount) * 100 if budget.amount > 0 else 0
    
    if percentage >= 100:
        return "exceeded"
    elif percentage >= 80:
        return "warning"
    else:
        return "normal"

@router.get("/", response_model=List[BudgetWithSpent])
async def get_budgets(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Si no se especifica mes/año, usar el actual
    if not month or not year:
        now = datetime.now()
        month = month or now.month
        year = year or now.year
    
    # Obtener presupuestos
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == month,
        Budget.year == year
    ).all()
    
    result = []
    for budget in budgets:
        # Calcular gastos en la categoría para el mes/año
        spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category == budget.category,
            Transaction.transaction_type == TransactionType.EXPENSE,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).scalar() or 0
        
        spent_amount = abs(spent)  # Los gastos son negativos
        percentage = (spent_amount / budget.amount) * 100 if budget.amount > 0 else 0
        status = calculate_budget_status(budget, spent_amount)
        
        budget_with_spent = BudgetWithSpent(
            **budget.__dict__,
            spent_amount=spent_amount,
            percentage=percentage,
            status=status
        )
        result.append(budget_with_spent)
    
    return result

@router.post("/", response_model=BudgetSchema)
async def create_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar si ya existe un presupuesto para esa categoría/mes/año
    existing_budget = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category == budget.category,
        Budget.month == budget.month,
        Budget.year == budget.year
    ).first()
    
    if existing_budget:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un presupuesto para esta categoría en este mes"
        )
    
    db_budget = Budget(
        **budget.dict(),
        user_id=current_user.id
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.put("/{budget_id}", response_model=BudgetSchema)
async def update_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    # Actualizar campos
    for field, value in budget_update.dict(exclude_unset=True).items():
        setattr(budget, field, value)
    
    db.commit()
    db.refresh(budget)
    return budget

@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    db.delete(budget)
    db.commit()
    return {"message": "Presupuesto eliminado exitosamente"}
