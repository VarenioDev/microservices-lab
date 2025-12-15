from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
from models import PaymentCreate
from payment_gateways import StripeGateway, YooMoneyGateway
import asyncio
import json
import aio_pika
import random

app = FastAPI(title="Payment Service", version="1.0.0")

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

# RabbitMQ settings
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
_rabbit_connection = None
_rabbit_channel = None

async def publish_event(routing_key: str, message: dict):
    global _rabbit_channel
    if _rabbit_channel is None:
        return
    body = json.dumps(message).encode()
    await _rabbit_channel.default_exchange.publish(
        aio_pika.Message(body=body, content_type="application/json"),
        routing_key=routing_key
    )

async def _on_order_created(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            order_id = payload.get("order_id")
            amount = payload.get("total_amount")
            user_id = payload.get("user_id")
            # Simulate payment processing (random success/failure)
            await asyncio.sleep(1)
            success = random.random() < 0.9
            payment_id = f"PAY-{order_id[-8:]}"
            if success:
                await publish_event("payment.succeeded", {
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "amount": amount
                })
                print(f"Payment succeeded for {order_id}")
            else:
                await publish_event("payment.failed", {
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "amount": amount,
                    "reason": "simulated_failure"
                })
                print(f"Payment failed for {order_id}")
        except Exception as e:
            print(f"Error processing order.created: {e}")

async def start_rabbitmq():
    global _rabbit_connection, _rabbit_channel
    try:
        _rabbit_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        _rabbit_channel = await _rabbit_connection.channel()
        await _rabbit_channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC)
        queue = await _rabbit_channel.declare_queue("payment-service.order-created", durable=True)
        await queue.bind("events", routing_key="order.created")
        await queue.consume(_on_order_created)
        print("Payment-service connected to RabbitMQ and consuming order.created events")
    except Exception as e:
        print(f"Could not connect to RabbitMQ: {e}")

async def stop_rabbitmq():
    global _rabbit_connection
    if _rabbit_connection:
        await _rabbit_connection.close()

@app.post("/create", response_model=Dict[str, Any])
async def create_payment(payment_data: PaymentCreate):
    """
    Создание платежной сессии
    """
    try:
        if payment_data.payment_method in ["card", "apple_pay", "google_pay"]:
            result = await stripe_gateway.create_payment(payment_data)
            gateway = "stripe"
        elif payment_data.payment_method == "yoomoney":
            result = await yoomoney_gateway.create_payment(payment_data)
            gateway = "yoomoney"
        else:
            raise HTTPException(status_code=400, detail="Unsupported payment method")
        
        return {
            "success": True,
            "gateway": gateway,
            "payment_data": result,
            "order_id": payment_data.order_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{payment_id}/status")
async def get_payment_status(payment_id: str, gateway: str = "stripe"):
    """
    Получение статуса платежа
    """
    try:
        if gateway == "stripe":
            status = await stripe_gateway.get_payment_status(payment_id)
        elif gateway == "yoomoney":
            status = await yoomoney_gateway.get_payment_status(payment_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid gateway")
        
        return {"success": True, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/{payment_id}/refund")
async def refund_payment(payment_id: str, amount: float = None, gateway: str = "stripe"):
    """
    Возврат платежа
    """
    try:
        if gateway == "stripe":
            result = await stripe_gateway.refund_payment(payment_id, amount)
        elif gateway == "yoomoney":
            # В реальном проекте - вызов API YooMoney для возврата
            result = {"status": "refund_initiated", "message": "Refund processed"}
        else:
            raise HTTPException(status_code=400, detail="Invalid gateway")
        
        return {"success": True, "refund": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Вебхуки от платежных систем
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Обработка вебхуков от Stripe
    """
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
            # Здесь можно обновить статус в вашей БД
        
        return {"success": True, "event": event["type"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhooks/yoomoney")
async def yoomoney_webhook(request: Request):
    """
    Обработка вебхуков от YooMoney
    """
    data = await request.json()
    
    notification_type = data.get("notification_type")
    
    if notification_type == "p2p-incoming":
        amount = data.get("amount")
        sender = data.get("sender")
        label = data.get("label")
        
        print(f"YooMoney payment received: {amount} from {sender} for order {label}")
        # Обновление статуса заказа
    
    return {"success": True}


# Startup / Shutdown for RabbitMQ
@app.on_event("startup")
async def on_startup():
    await asyncio.sleep(2)
    await start_rabbitmq()

@app.on_event("shutdown")
async def on_shutdown():
    await stop_rabbitmq()

# Health check для Consul
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-service"}

@app.get("/")
async def root():
    return {"message": "Payment Service is running"}