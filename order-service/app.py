from fastapi import FastAPI, HTTPException, Query, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import asyncio
import json
import os
import aio_pika
import httpx
import time

from models import OrderCreate, OrderUpdate, OrderResponse, UserOrdersResponse, OrderStatus, PaymentStatus
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="Order Service API",
    description="Сервис управления заказами",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Временное хранилище заказов
orders_db: Dict[str, dict] = {}

# RabbitMQ connection
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
_rabbit_connection = None
_rabbit_channel = None

# Middleware для логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}ms")
    
    return response

async def publish_event(routing_key: str, message: dict):
    """Publish an event to the 'events' exchange"""
    global _rabbit_connection, _rabbit_channel
    if _rabbit_channel is None:
        return
    
    body = json.dumps(message).encode()
    await _rabbit_channel.default_exchange.publish(
        aio_pika.Message(body=body, content_type="application/json"),
        routing_key=routing_key
    )

async def _on_payment_event(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            routing = message.routing_key
            order_id = payload.get("order_id")
            if not order_id or order_id not in orders_db:
                print(f"Payment event for unknown order {order_id}")
                return

            order = orders_db[order_id]
            if routing == "payment.succeeded":
                order["payment_status"] = PaymentStatus.PAID.value
                order["status"] = OrderStatus.PROCESSING.value
                order["updated_at"] = get_current_time()
                print(f"Order {order_id} marked as PAID")
            elif routing == "payment.failed":
                order["payment_status"] = PaymentStatus.FAILED.value
                order["status"] = OrderStatus.CANCELLED.value
                order["updated_at"] = get_current_time()
                print(f"Order {order_id} cancelled due to payment failure")
                await publish_event("order.cancelled", {"order_id": order_id, "reason": payload.get("reason")})
        except Exception as e:
            print(f"Error handling payment event: {e}")

async def start_rabbitmq():
    global _rabbit_connection, _rabbit_channel
    try:
        _rabbit_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        _rabbit_channel = await _rabbit_connection.channel()

        await _rabbit_channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC)

        queue = await _rabbit_channel.declare_queue("order-service.payment-events", durable=True)
        await queue.bind("events", routing_key="payment.*")
        await queue.consume(_on_payment_event)
        print("Order-service connected to RabbitMQ and consuming payment events")
    except Exception as e:
        print(f"Could not connect to RabbitMQ: {e}")

async def stop_rabbitmq():
    global _rabbit_connection
    if _rabbit_connection:
        await _rabbit_connection.close()

# Helper функции
def generate_order_id():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

def get_current_time():
    return datetime.utcnow().isoformat()

def calculate_total(items: List[Dict]) -> float:
    return sum(item["price"] * item["quantity"] for item in items)

# REST API Endpoints
@app.get("/api/v1/orders", response_model=List[OrderResponse])
async def get_orders(
    user_id: Optional[str] = Query(None, description="Фильтр по пользователю"),
    status: Optional[OrderStatus] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(100, ge=1, le=500, description="Лимит результатов")
):
    """Получить список заказов с фильтрацией"""
    filtered_orders = list(orders_db.values())
    
    if user_id:
        filtered_orders = [order for order in filtered_orders if order["user_id"] == user_id]
    
    if status:
        filtered_orders = [order for order in filtered_orders if order["status"] == status.value]
    
    return filtered_orders[:limit]

@app.get("/api/v1/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Получить заказ по ID"""
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/v1/orders/user/{user_id}", response_model=UserOrdersResponse)
async def get_user_orders(
    user_id: str,
    status: Optional[OrderStatus] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=200, description="Лимит результатов")
):
    """Получить все заказы пользователя"""
    user_orders = [order for order in orders_db.values() if order["user_id"] == user_id]
    
    if status:
        user_orders = [order for order in user_orders if order["status"] == status.value]
    
    return UserOrdersResponse(
        orders=user_orders[:limit],
        total=len(user_orders),
        user_id=user_id
    )

@app.post("/api/v1/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate):
    """Создать новый заказ"""
    order_id = generate_order_id()
    current_time = get_current_time()
    
    items_dict = [item.dict() for item in order_data.items]
    total_amount = calculate_total(items_dict)
    
    new_order = {
        "id": order_id,
        "user_id": order_data.user_id,
        "items": items_dict,
        "total_amount": total_amount,
        "status": OrderStatus.PENDING.value,
        "payment_status": PaymentStatus.PENDING.value,
        "shipping_address": order_data.shipping_address,
        "payment_method": order_data.payment_method,
        "tracking_number": None,
        "notes": None,
        "created_at": current_time,
        "updated_at": current_time
    }
    
    orders_db[order_id] = new_order
    asyncio.create_task(publish_event("order.created", {
        "order_id": order_id,
        "user_id": order_data.user_id,
        "total_amount": total_amount,
        "items": items_dict,
        "shipping_address": order_data.shipping_address
    }))
    return new_order

@app.put("/api/v1/orders/{order_id}", response_model=OrderResponse)
async def update_order(order_id: str, order_update: OrderUpdate):
    """Обновить заказ"""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = orders_db[order_id]
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if hasattr(value, 'value'):
                order[field] = value.value
            else:
                order[field] = value
    
    order["updated_at"] = get_current_time()
    
    return order

@app.delete("/api/v1/orders/{order_id}")
async def delete_order(order_id: str):
    """Удалить заказ"""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    
    deleted_order = orders_db.pop(order_id)
    return {"message": f"Order {order_id} deleted successfully"}

@app.get("/api/v1/orders/{order_id}/items")
async def get_order_items(order_id: str):
    """Получить товары из заказа"""
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order_id,
        "items": order["items"],
        "total_items": len(order["items"]),
        "total_amount": order["total_amount"]
    }

# Метрики для Prometheus
@app.get("/metrics")
async def metrics():
    """Эндпоинт для метрик Prometheus"""
    # Эта функция будет автоматически инструментирована prometheus-fastapi-instrumentator
    pass

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "order-service",
        "order_count": len(orders_db)
    }

@app.get("/")
async def root():
    return {
        "message": "Order Service API",
        "docs": "/api/docs",
        "total_orders": len(orders_db)
    }

# Startup / Shutdown events
@app.on_event("startup")
async def on_startup():
    # Инициализация Prometheus метрик
    Instrumentator().instrument(app).expose(app)
    
    # RabbitMQ подключение
    await asyncio.sleep(2)
    await start_rabbitmq()

@app.on_event("shutdown")
async def on_shutdown():
    await stop_rabbitmq()