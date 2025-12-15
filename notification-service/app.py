from fastapi import FastAPI
import asyncio
import os
import json
import aio_pika

app = FastAPI(title="Notification Service", version="1.0.0")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
_conn = None
_channel = None

async def _on_event(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            rk = message.routing_key
            # Simple notification handling: just log
            print(f"[notification] event={rk} payload={payload}")
        except Exception as e:
            print(f"Error in notification consumer: {e}")

async def start_consumer():
    global _conn, _channel
    try:
        _conn = await aio_pika.connect_robust(RABBITMQ_URL)
        _channel = await _conn.channel()
        await _channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC)
        q = await _channel.declare_queue("notifications.all", durable=True)
        await q.bind("events", routing_key="#")
        await q.consume(_on_event)
        print("Notification service connected to RabbitMQ and consuming all events")
    except Exception as e:
        print(f"Notification start error: {e}")

async def stop_consumer():
    global _conn
    if _conn:
        await _conn.close()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "notification-service"}


@app.on_event("startup")
async def startup():
    await asyncio.sleep(2)
    await start_consumer()


@app.on_event("shutdown")
async def shutdown():
    await stop_consumer()


@app.get("/")
async def root():
    return {"message": "Notification service running"}
