from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import uuid
import time
import asyncio
from pydantic import BaseModel, Field
from enum import Enum

# Модели (упрощенные)
class PaymentMethod(str, Enum):
    CARD = "card"
    YOOMONEY = "yoomoney"
    SBP = "sbp"

class PaymentCreate(BaseModel):
    order_id: str = Field(..., description="ID заказа")
    user_id: str = Field(..., description="ID пользователя")
    amount: float = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(default="RUB")
    payment_method: PaymentMethod = Field(..., description="Метод оплаты")
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    payment_url: Optional[str]
    amount: float
    currency: str
    order_id: str

app = FastAPI(title="Payment Service (Stub)", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Имитация базы данных
payments_db = {}

# Заглушка для платежных шлюзов
class StubPaymentGateway:
    async def create_payment(self, payment_data: PaymentCreate) -> Dict[str, Any]:
        """Создание фиктивного платежа"""
        payment_id = str(uuid.uuid4())
        
        # Генерируем фиктивные данные в зависимости от метода оплаты
        if payment_data.payment_method in ["card", "apple_pay", "google_pay"]:
            response = {
                "payment_id": f"pi_{payment_id[:14]}",
                "client_secret": f"pi_{payment_id[:14]}_secret",
                "status": "succeeded",
                "amount": payment_data.amount,
                "currency": payment_data.currency
            }
        elif payment_data.payment_method == "yoomoney":
            response = {
                "payment_id": payment_id,
                "payment_url": f"https://example.com/pay/{payment_id}",
                "status": "pending",
                "amount": payment_data.amount,
                "currency": payment_data.currency
            }
        else:
            response = {
                "payment_id": payment_id,
                "status": "created",
                "amount": payment_data.amount,
                "currency": payment_data.currency
            }
        
        return response
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Получение фиктивного статуса"""
        # Проверяем, есть ли платеж в нашей "базе"
        if payment_id in payments_db:
            return payments_db[payment_id]
        
        # Иначе возвращаем фиктивный статус
        return {
            "payment_id": payment_id,
            "status": "succeeded",
            "message": "Payment completed successfully (stub)",
            "timestamp": time.time()
        }
    
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Фиктивный возврат платежа"""
        return {
            "refund_id": f"re_{uuid.uuid4().hex[:8]}",
            "status": "succeeded",
            "amount": amount or 100.0,
            "message": "Refund processed successfully (stub)"
        }

# Инициализируем заглушку
stub_gateway = StubPaymentGateway()

# Endpoints
@app.get("/")
async def root():
    return {
        "message": "Payment Service Stub",
        "version": "1.0.0",
        "note": "This is a stub service - no real payments are processed",
        "endpoints": {
            "health": "GET /health",
            "create": "POST /create",
            "status": "GET /{payment_id}/status",
            "refund": "POST /{payment_id}/refund"
        }
    }

@app.get("/health")
async def health_check():
    """Health check для тестов"""
    return {
        "status": "healthy",
        "service": "payment-service-stub",
        "timestamp": time.time(),
        "note": "This is a stub service for testing"
    }

@app.post("/create", response_model=Dict[str, Any])
async def create_payment(payment_data: PaymentCreate):
    """
    Создание фиктивного платежа
    """
    try:
        # Используем заглушку вместо реального шлюза
        result = await stub_gateway.create_payment(payment_data)
        
        # Сохраняем в "базу"
        payments_db[result.get("payment_id", str(uuid.uuid4()))] = {
            **result,
            "order_id": payment_data.order_id,
            "user_id": payment_data.user_id,
            "gateway": "stub",
            "timestamp": time.time(),
            "description": payment_data.description
        }
        
        return {
            "success": True,
            "gateway": "stub",
            "payment_data": result,
            "order_id": payment_data.order_id,
            "message": "Payment created successfully (stub)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Payment creation failed in stub"
        }

@app.get("/{payment_id}/status")
async def get_payment_status(payment_id: str, gateway: str = "stub"):
    """
    Получение статуса фиктивного платежа
    """
    try:
        result = await stub_gateway.get_payment_status(payment_id)
        return {
            "success": True,
            "status": result,
            "source": "stub_gateway"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Status check failed in stub"
        }

@app.post("/{payment_id}/refund")
async def refund_payment(payment_id: str, amount: Optional[float] = None):
    """
    Фиктивный возврат платежа
    """
    try:
        result = await stub_gateway.refund_payment(payment_id, amount)
        return {
            "success": True,
            "refund": result,
            "message": "Refund processed (stub)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Refund failed in stub"
        }

@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """
    Заглушка для Circuit Breaker статуса
    """
    return {
        "circuit_breakers": [
            {
                "name": "create_payment",
                "state": "CLOSED",
                "failure_count": 0,
                "open_until": None
            },
            {
                "name": "get_status",
                "state": "CLOSED",
                "failure_count": 0,
                "open_until": None
            }
        ],
        "note": "Circuit breakers are disabled in stub mode",
        "total": 2
    }

# Вебхуки-заглушки
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Заглушка для Stripe webhook"""
    return {
        "success": True,
        "message": "Webhook received (stub)",
        "event": "payment_intent.succeeded",
        "note": "This is a stub - no real webhook processing"
    }

@app.post("/webhooks/yoomoney")
async def yoomoney_webhook(request: Request):
    """Заглушка для YooMoney webhook"""
    return {
        "success": True,
        "message": "Webhook received (stub)",
        "event": "p2p-incoming",
        "note": "This is a stub - no real webhook processing"
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Starting Payment Service STUB")
    print("Port: 5003")
    print("Mode: Stub (no real payments)")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=5003)