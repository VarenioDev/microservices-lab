from fastapi import FastAPI, HTTPException, Request
import os
import httpx

CONSUL_ADDR = os.environ.get("CONSUL_ADDR", "http://consul:8500")

app = FastAPI(title="Service Discovery")


@app.get("/")
async def root():
    return {"message": "Service Discovery (Consul client) running"}


@app.get("/services")
async def services():
    url = f"{CONSUL_ADDR}/v1/agent/services"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()


@app.get("/catalog/services")
async def catalog_services():
    url = f"{CONSUL_ADDR}/v1/catalog/services"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()


@app.post("/register")
async def register_service(payload: dict):
    url = f"{CONSUL_ADDR}/v1/agent/service/register"
    async with httpx.AsyncClient() as client:
        resp = await client.put(url, json=payload, timeout=10.0)
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail=resp.text)
        return {"result": "registered"}


@app.put("/kv/{key:path}")
async def kv_put(key: str, request: Request):
    body = await request.body()
    url = f"{CONSUL_ADDR}/v1/kv/{key}"
    async with httpx.AsyncClient() as client:
        resp = await client.put(url, content=body, timeout=10.0)
        resp.raise_for_status()
        return {"result": True}


@app.get("/kv/{key:path}")
async def kv_get(key: str):
    url = f"{CONSUL_ADDR}/v1/kv/{key}?raw"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            return {"value": resp.text}
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Key not found")
        raise HTTPException(status_code=500, detail=resp.text)
