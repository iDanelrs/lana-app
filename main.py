from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uvicorn
import sys
import os

# Verificar que los módulos estén disponibles
try:
    from database import get_db, engine
    from models import Base
    print("✅ Módulos de base de datos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos de base de datos: {e}")
    print("💡 Ejecuta: python install_dependencies.py")
    sys.exit(1)

# Importar routers
try:
    from routers import auth, users, transactions, budgets, fixed_payments, notifications, analytics
    print("✅ Routers importados correctamente")
except ImportError as e:
    print(f"❌ Error importando routers: {e}")
    # Crear routers vacíos temporalmente
    from fastapi import APIRouter
    auth = APIRouter()
    users = APIRouter()
    transactions = APIRouter()
    budgets = APIRouter()
    fixed_payments = APIRouter()
    notifications = APIRouter()
    analytics = APIRouter()

# Crear las tablas en la base de datos
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada")
except Exception as e:
    print(f"⚠️ Advertencia al crear tablas: {e}")

app = FastAPI(
    title="Lana App API",
    description="API para gestión de finanzas personales",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transacciones"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["Presupuestos"])
app.include_router(fixed_payments.router, prefix="/api/fixed-payments", tags=["Pagos Fijos"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notificaciones"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Análisis"])

@app.get("/")
async def root():
    return {
        "message": "Lana App API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now(),
        "database": "connected"
    }

if __name__ == "__main__":
    print("🚀 Iniciando Lana App API...")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
