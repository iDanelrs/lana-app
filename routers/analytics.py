from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models import User, Transaction, Budget, FixedPayment, TransactionType
from schemas import (
    MonthlyAnalysis,
    CategoryAnalysis,
    DashboardData,
    BudgetWithSpent,
    FixedPaymentWithStatus,
    Transaction as TransactionSchema
)
from auth import get_current_user
from routers.budgets import calculate_budget_status
from routers.fixed_payments import calculate_next_due_date, get_payment_status

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
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
    
    # Análisis mensual
    income_sum = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.INCOME,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).scalar() or 0
    
    expense_sum = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.EXPENSE,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).scalar() or 0
    
    expense_sum = abs(expense_sum)  # Los gastos son negativos
    
    transactions_count = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).scalar() or 0
    
    monthly_analysis = MonthlyAnalysis(
        total_income=income_sum,
        total_expenses=expense_sum,
        balance=income_sum - expense_sum,
        transactions_count=transactions_count
    )
    
    # Análisis por categorías (solo gastos)
    category_data = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.EXPENSE,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).group_by(Transaction.category).all()
    
    category_breakdown = []
    for category, total, count in category_data:
        amount = abs(total)
        percentage = (amount / expense_sum * 100) if expense_sum > 0 else 0
        category_breakdown.append(CategoryAnalysis(
            category=category,
            amount=amount,
            percentage=percentage,
            transaction_count=count
        ))
    
    # Transacciones recientes
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()
    
    # Estado de presupuestos
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == month,
        Budget.year == year
    ).all()
    
    budget_status = []
    for budget in budgets:
        spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category == budget.category,
            Transaction.transaction_type == TransactionType.EXPENSE,
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).scalar() or 0
        
        spent_amount = abs(spent)
        percentage = (spent_amount / budget.amount) * 100 if budget.amount > 0 else 0
        status = calculate_budget_status(budget, spent_amount)
        
        budget_status.append(BudgetWithSpent(
            **budget.__dict__,
            spent_amount=spent_amount,
            percentage=percentage,
            status=status
        ))
    
    # Próximos pagos
    payments = db.query(FixedPayment).filter(
        FixedPayment.user_id == current_user.id,
        FixedPayment.is_active == True
    ).all()
    
    upcoming_payments = []
    for payment in payments:
        next_due = calculate_next_due_date(payment.due_day)
        days_until_due = (next_due.date() - datetime.now().date()).days
        
        if days_until_due <= 7:  # Próximos 7 días
            status = get_payment_status(payment, days_until_due)
            upcoming_payments.append(FixedPaymentWithStatus(
                **payment.__dict__,
                next_due=next_due,
                days_until_due=days_until_due,
                status=status
            ))
    
    return DashboardData(
        monthly_analysis=monthly_analysis,
        category_breakdown=category_breakdown,
        recent_transactions=recent_transactions,
        budget_status=budget_status,
        upcoming_payments=upcoming_payments
    )

@router.get("/monthly-trend")
async def get_monthly_trend(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # Obtener datos mensuales
    monthly_data = db.query(
        extract('year', Transaction.date).label('year'),
        extract('month', Transaction.date).label('month'),
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date
    ).group_by(
        extract('year', Transaction.date),
        extract('month', Transaction.date),
        Transaction.transaction_type
    ).all()
    
    # Organizar datos por mes
    trend_data = {}
    for year, month, transaction_type, total in monthly_data:
        key = f"{int(year)}-{int(month):02d}"
        if key not in trend_data:
            trend_data[key] = {"income": 0, "expenses": 0}
        
        if transaction_type == TransactionType.INCOME:
            trend_data[key]["income"] = total
        else:
            trend_data[key]["expenses"] = abs(total)
    
    return trend_data

@router.get("/category-trend/{category}")
async def get_category_trend(
    category: str,
    months: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    monthly_data = db.query(
        extract('year', Transaction.date).label('year'),
        extract('month', Transaction.date).label('month'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.category == category,
        Transaction.transaction_type == TransactionType.EXPENSE,
        Transaction.date >= start_date
    ).group_by(
        extract('year', Transaction.date),
        extract('month', Transaction.date)
    ).all()
    
    trend_data = {}
    for year, month, total in monthly_data:
        key = f"{int(year)}-{int(month):02d}"
        trend_data[key] = abs(total)
    
    return trend_data
