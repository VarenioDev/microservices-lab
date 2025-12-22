from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import os
import asyncio
import threading
import random
import time
from contextlib import asynccontextmanager

# Circuit Breaker
from circuitbreaker import circuit, CircuitBreakerMonitor

# gRPC
import grpc
from concurrent import futures

# Импорт сгенерированных gRPC файлов
import payment_service_pb2
import payment_service_pb2_grpc

from models import PaymentCreate
from payment_gateways import StripeGateway, YooMoneyGateway

# Circuit Breaker state для мониторинга
cb_monitor = CircuitBreakerMonitor()

# Имитация базы данных платежей
payments_db = {}

class PaymentService(payment_service_pb2_grpc.PaymentServiceServicer):
    def __init__(self, stripe_gateway: StripeGateway, yoomoney_gateway: YooMoneyGateway):
        self.stripe_gateway = stripe_gateway
        self.yoomoney_gateway = yoomoney_gateway
    
    @circuit(failure_threshold=5, recovery_timeout=30)
    def ProcessPayment(self, request, context):
        """Обработка платежа через gRPC с Circuit Breaker"""
        try:
            # Имитация случайных сбоев (30% вероятность для теста Circuit Breaker)
            if random.random() < 0.3:
                raise Exception("Payment gateway unavailable")
            
            # Преобразуем gRPC запрос в PaymentCreate
            payment_data = PaymentCreate(
                order_id=request.order_id,
                user_id=request.user_id,
                amount=request.amount,
                currency=request.currency,
                payment_method=request.payment_method,
                description=f"Payment for order {request.order_id}"
            )
            
            # Выбор шлюза
            if request.payment_method in ["card", "apple_pay", "google_pay"]:
                result = asyncio.run(self.stripe_gateway.create_payment(payment_data))
                gateway = "stripe"
            elif request.payment_method == "yoomoney":
                result = asyncio.run(self.yoomoney_gateway.create_payment(payment_data))
                gateway = "yoomoney"
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Unsupported payment method")
                return payment_service_pb2.PaymentResponse()
            
            # Сохраняем в базу
            payments_db[result.get("payment_id", "")] = {
                **result,
                "order_id": request.order_id,
                "gateway": gateway,
                "timestamp": time.time()
            }
            
            return payment_service_pb2.PaymentResponse(
                payment_id=result.get("payment_id", ""),
                status=result.get("status", "pending"),
                message=f"Payment processed via {gateway}",
                gateway=gateway
            )
            
        except Exception as e:
            # Fallback при сбое Circuit Breaker
            return payment_service_pb2.PaymentResponse(
                payment_id="",
                status="processing",
                message="Payment is being processed (fallback mode)",
                gateway="fallback"
            )
    
    def GetPaymentStatus(self, request, context):
        """Получение статуса платежа через gRPC"""
        payment_id = request.payment_id
        
        if payment_id in payments_db:
            payment = payments_db[payment_id]
            return payment_service_pb2.PaymentStatusResponse(
                payment_id=payment_id,
                status=payment.get("status", "unknown"),
                message=f"Payment details for {payment.get('order_id', 'unknown')}"
            )
        else:
            # Пробуем получить статус из шлюза
            try:
                if request.gateway == "stripe":
                    status = asyncio.run(self.stripe_gateway.get_payment_status(payment_id))
                elif request.gateway == "yoomoney":
                    status = asyncio.run(self.yoomoney_gateway.get_payment_status(payment_id))
                else:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details("Invalid gateway")
                    return payment_service_pb2.PaymentStatusResponse()
                
                return payment_service_pb2.PaymentStatusResponse(
                    payment_id=payment_id,
                    status=status.get("status", "unknown"),
                    message="Status retrieved from payment gateway"
                )
            except Exception as e:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Payment not found: {str(e)}")
                return payment_service_pb2.PaymentStatusResponse()

def run_grpc_server(stripe_gateway, yoomoney_gateway):
    """Запуск gRPC сервера"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    payment_service_pb2_grpc.add_PaymentServiceServicer_to_server(
        PaymentService(stripe_gateway, yoomoney_gateway), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan для управления запуском/остановкой gRPC сервера"""
    # Запускаем gRPC сервер в отдельном потоке
    grpc_thread = threading.Thread(
        target=run_grpc_server,
        args=(stripe_gateway, yoomoney_gateway),
        daemon=True
    )
    grpc_thread.start()
    print("gRPC server thread started")
    yield
    # Очистка при завершении
    print("Shutting down...")

app = FastAPI(title="Payment Service", version="2.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация платежных шлюзов
stripe_gateway = StripeGateway()
yoomoney_gateway = YooMoneyGateway()

# Circuit Breaker для HTTP endpoints
@app.post("/create", response_model=Dict[str, Any])
@circuit(failure_threshold=5, recovery_timeout=30)
async def create_payment(payment_data: PaymentCreate):
    """
    Создание платежной сессии с Circuit Breaker
    """
    try:
        # Имитация сбоя для тестирования Circuit Breaker (20% вероятность)
        if random.random() < 0.2:
            raise Exception("Simulated gateway failure for Circuit Breaker test")
        
        if payment_data.payment_method in ["card", "apple_pay", "google_pay"]:
            result = await stripe_gateway.create_payment(payment_data)
            gateway = "stripe"
        elif payment_data.payment_method == "yoomoney":
            result = await yoomoney_gateway.create_payment(payment_data)
            gateway = "yoomoney"
        else:
            raise HTTPException(status_code=400, detail="Unsupported payment method")
        
        # Сохраняем в базу
        payments_db[result.get("payment_id", "")] = {
            **result,
            "order_id": payment_data.order_id,
            "gateway": gateway,
            "timestamp": time.time()
        }
        
        return {
            "success": True,
            "gateway": gateway,
            "payment_data": result,
            "order_id": payment_data.order_id
        }
    except Exception as e:
        # Fallback при срабатывании Circuit Breaker
        return {
            "success": True,
            "gateway": "fallback",
            "payment_data": {
                "payment_id": "",
                "status": "processing",
                "message": "Payment is being processed (fallback mode)",
                "amount": payment_data.amount,
                "currency": payment_data.currency
            },
            "order_id": payment_data.order_id
        }

@app.get("/{payment_id}/status")
@circuit(failure_threshold=3, recovery_timeout=20)
async def get_payment_status(payment_id: str, gateway: str = "stripe"):
    """
    Получение статуса платежа с Circuit Breaker
    """
    try:
        # Проверяем локальную базу
        if payment_id in payments_db:
            return {
                "success": True,
                "status": payments_db[payment_id],
                "source": "local_cache"
            }
        
        # Запрашиваем у шлюза
        if gateway == "stripe":
            status = await stripe_gateway.get_payment_status(payment_id)
        elif gateway == "yoomoney":
            status = await yoomoney_gateway.get_payment_status(payment_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid gateway")
        
        return {"success": True, "status": status}
    except Exception as e:
        # Fallback
        return {
            "success": True,
            "status": {
                "payment_id": payment_id,
                "status": "processing",
                "message": "Status check in progress (fallback)"
            },
            "source": "fallback"
        }

@app.post("/{payment_id}/refund")
@circuit(failure_threshold=3, recovery_timeout=20)
async def refund_payment(payment_id: str, amount: Optional[float] = None, gateway: str = "stripe"):
    """
    Возврат платежа с Circuit Breaker
    """
    try:
        if gateway == "stripe":
            result = await stripe_gateway.refund_payment(payment_id, amount)
        elif gateway == "yoomoney":
            result = {"status": "refund_initiated", "message": "Refund processed"}
        else:
            raise HTTPException(status_code=400, detail="Invalid gateway")
        
        return {"success": True, "refund": result}
    except Exception as e:
        # Fallback
        return {
            "success": True,
            "refund": {
                "status": "processing",
                "message": "Refund request received (fallback mode)"
            }
        }

# Мониторинг Circuit Breaker
@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Статус всех Circuit Breaker'ов"""
    breakers = []
    for cb in cb_monitor.get_circuits():
        breakers.append({
            "name": cb.name,
            "state": cb.state.name,
            "failure_count": cb.failure_count,
            "open_until": cb.open_remaining if hasattr(cb, 'open_remaining') else None
        })
    
    return {
        "circuit_breakers": breakers,
        "total": len(breakers)
    }

@app.post("/circuit-breaker/reset/{name}")
async def reset_circuit_breaker(name: str):
    """Сброс Circuit Breaker'а"""
    for cb in cb_monitor.get_circuits():
        if cb.name == name:
            cb.close()
            return {"success": True, "message": f"Circuit breaker '{name}' reset"}
    
    return {"success": False, "message": f"Circuit breaker '{name}' not found"}

# Вебхуки (без изменений)
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            print(f"Payment succeeded: {payment_intent['id']}")
        
        return {"success": True, "event": event["type"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhooks/yoomoney")
async def yoomoney_webhook(request: Request):
    data = await request.json()
    
    notification_type = data.get("notification_type")
    
    if notification_type == "p2p-incoming":
        amount = data.get("amount")
        sender = data.get("sender")
        label = data.get("label")
        
        print(f"YooMoney payment received: {amount} from {sender} for order {label}")
    
    return {"success": True}

# Health checks
@app.get("/health")
async def health_check():
    """Health check для Consul"""
    return {
        "status": "healthy",
        "service": "payment-service",
        "grpc": "enabled",
        "circuit_breaker": "enabled"
    }

@app.get("/health/grpc")
async def grpc_health_check():
    """Health check для gRPC соединения"""
    try:
        # Пробуем подключиться к gRPC серверу
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = payment_service_pb2_grpc.PaymentServiceStub(channel)
            # Пустой запрос для проверки
            response = stub.GetPaymentStatus(
                payment_service_pb2.PaymentStatusRequest(payment_id="test", gateway="stripe"),
                timeout=2
            )
            return {"grpc": "healthy"}
    except Exception as e:
        return {"grpc": "unhealthy", "error": str(e)}

@app.get("/")
async def root():
    return {
        "message": "Payment Service with gRPC and Circuit Breaker",
        "version": "2.0.0",
        "endpoints": {
            "create_payment": "POST /create",
            "get_status": "GET /{payment_id}/status",
            "refund": "POST /{payment_id}/refund",
            "circuit_breaker_status": "GET /circuit-breaker/status",
            "health": "GET /health",
            "grpc_health": "GET /health/grpc"
        },
        "grpc_port": 50051,
        "http_port": 5000
    }