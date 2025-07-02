from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional, List
from models import TransactionType, NotificationType

# Esquemas de Usuario
class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Esquemas de Autenticación
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Esquemas de Transacciones
class TransactionBase(BaseModel):
    amount: float
    description: str
    category: str
    transaction_type: TransactionType
    date: datetime

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None

class Transaction(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Esquemas de Presupuestos
class BudgetBase(BaseModel):
    category: str
    amount: float
    month: int
    year: int
    
    @validator('month')
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError('El mes debe estar entre 1 y 12')
        return v

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: Optional[float] = None

class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BudgetWithSpent(Budget):
    spent_amount: float
    percentage: float
    status: str

# Esquemas de Pagos Fijos
class FixedPaymentBase(BaseModel):
    name: str
    amount: float
    due_day: int
    is_active: bool = True
    auto_register: bool = False
    
    @validator('due_day')
    def validate_due_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError('El día debe estar entre 1 y 31')
        return v

class FixedPaymentCreate(FixedPaymentBase):
    pass

class FixedPaymentUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_day: Optional[int] = None
    is_active: Optional[bool] = None
    auto_register: Optional[bool] = None

class FixedPayment(FixedPaymentBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FixedPaymentWithStatus(FixedPayment):
    next_due: datetime
    days_until_due: int
    status: str

# Esquemas de Notificaciones
class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: NotificationType

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    sent_via_email: bool
    sent_via_sms: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationSettingsBase(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = True
    budget_alerts: bool = True
    payment_reminders: bool = True
    weekly_reports: bool = False
    monthly_reports: bool = True

class NotificationSettingsUpdate(NotificationSettingsBase):
    pass

class NotificationSettings(NotificationSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Esquemas de Análisis
class MonthlyAnalysis(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    transactions_count: int

class CategoryAnalysis(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int

class DashboardData(BaseModel):
    monthly_analysis: MonthlyAnalysis
    category_breakdown: List[CategoryAnalysis]
    recent_transactions: List[Transaction]
    budget_status: List[BudgetWithSpent]
    upcoming_payments: List[FixedPaymentWithStatus]
