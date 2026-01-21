from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import time

app = FastAPI(title="Payment Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PaymentMethod(str, Enum):
    CARD = "card"
    YOOMONEY = "yoomoney"
    SBP = "sbp"


class PaymentCreate(BaseModel):
    order_id: str = Field(...)
    user_id: str = Field(...)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="RUB")
    payment_method: PaymentMethod = Field(...)
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    payment_url: Optional[str]
    amount: float
    currency: str
    order_id: str


payments_db = {}


class StubPaymentGateway:
    async def create_payment(self, payment_data: PaymentCreate) -> Dict[str, Any]:
        payment_id = str(uuid.uuid4())
        
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
        if payment_id in payments_db:
            return payments_db[payment_id]
        
        return {
            "payment_id": payment_id,
            "status": "succeeded",
            "message": "Payment completed successfully (stub)",
            "timestamp": time.time()
        }
    
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        return {
            "refund_id": f"re_{uuid.uuid4().hex[:8]}",
            "status": "succeeded",
            "amount": amount or 100.0,
            "message": "Refund processed successfully (stub)"
        }


stub_gateway = StubPaymentGateway()


@app.get("/")
async def root():
    return {
        "message": "Payment Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "create": "POST /create",
            "status": "GET /{payment_id}/status",
            "refund": "POST /{payment_id}/refund"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "payment-service",
        "timestamp": time.time()
    }


@app.post("/create", response_model=Dict[str, Any])
async def create_payment(payment_data: PaymentCreate):
    try:
        result = await stub_gateway.create_payment(payment_data)
        
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
            "message": "Payment created successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Payment creation failed"
        }


@app.get("/{payment_id}/status")
async def get_payment_status(payment_id: str, gateway: str = "stub"):
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
            "message": "Status check failed"
        }


@app.post("/{payment_id}/refund")
async def refund_payment(payment_id: str, amount: Optional[float] = None):
    try:
        result = await stub_gateway.refund_payment(payment_id, amount)
        return {
            "success": True,
            "refund": result,
            "message": "Refund processed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Refund failed"
        }


@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
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
        "total": 2
    }


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    return {
        "success": True,
        "message": "Webhook received",
        "event": "payment_intent.succeeded"
    }


@app.post("/webhooks/yoomoney")
async def yoomoney_webhook(request: Request):
    return {
        "success": True,
        "message": "Webhook received",
        "event": "p2p-incoming"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
