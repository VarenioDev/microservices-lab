# End-to-End Testing Results - Microservices Lab

## Test Summary

| Test | Status | Description |
|------|--------|-------------|
| Registration | ✅ PASSED | New user successfully registered in Auth Service |
| Authentication | ✅ PASSED | JWT token generated for user login |
| Catalog Browse | ✅ PASSED | Retrieved all products from Catalog Service |
| Product Details | ✅ PASSED | Fetched individual product info |
| Create Order | ✅ PASSED | Order created and stored in Order Service |
| Payment | ✅ PASSED | Payment processed via Payment Service |
| Order Status | ✅ PASSED | Order status retrieved successfully |
| User Orders | ✅ PASSED | User order history retrieved |
| API Gateway | ✅ PASSED | All services accessible via nginx gateway |
| Notifications | ✅ PASSED | Notification service health verified |
| Admin Add Product | ✅ PASSED | Admin created new product in catalog |

**Total: 11/11 Tests Passed (100%)**

---

## Data Flow Demonstration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            END-TO-END DATA FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

1. USER REGISTRATION & AUTHENTICATION
   ┌──────────┐     POST /register      ┌──────────────┐
   │  Client  │ ────────────────────►   │ Auth Service │
   │          │ ◄──────────────────────  │  (port 5001) │
   └──────────┘     User Created        └──────────────┘
        │                                      │
        │        POST /login                   │
        │ ────────────────────────────────────►│
        │ ◄────────────────────────────────────│
        │         JWT Token                    │
        ▼

2. BROWSE CATALOG
   ┌──────────┐     GET /products       ┌────────────────┐
   │  Client  │ ────────────────────►   │ Catalog Service│
   │          │ ◄──────────────────────  │  (port 5002)   │
   └──────────┘     Product List        └────────────────┘
        │
        │        GET /products/{id}
        │ ────────────────────────────►
        │ ◄────────────────────────────
        │        Product Details
        ▼

3. CREATE ORDER
   ┌──────────┐     POST /api/v1/orders  ┌───────────────┐
   │  Client  │ ─────────────────────►   │ Order Service │
   │          │ ◄─────────────────────   │  (port 5004)  │
   └──────────┘     Order Created        └───────────────┘
        │                                      │
        │                                      │ publish event
        │                                      ▼
        │                               ┌───────────────┐
        │                               │   RabbitMQ    │
        │                               │  (port 5672)  │
        │                               └───────────────┘
        │                                      │
        │                                      │ consume
        │                                      ▼
        │                               ┌────────────────────┐
        │                               │Notification Service│
        │                               │   (port 5006)      │
        │                               └────────────────────┘
        ▼

4. PROCESS PAYMENT
   ┌──────────┐     POST /create        ┌─────────────────┐
   │  Client  │ ────────────────────►   │ Payment Service │
   │          │ ◄──────────────────────  │  (port 5003)    │
   └──────────┘     Payment Success     └─────────────────┘
        │
        ▼

5. CHECK ORDER STATUS
   ┌──────────┐   GET /api/v1/orders/{id}  ┌───────────────┐
   │  Client  │ ─────────────────────────► │ Order Service │
   │          │ ◄───────────────────────── │  (port 5004)  │
   └──────────┘       Order Details        └───────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY ROUTING                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

                         ┌────────────────────┐
                         │    API Gateway     │
                         │  (nginx:8080)      │
                         └─────────┬──────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    /auth/* → :5001       /catalog/* → :5002      /orders/* → :5004
    /payments/* → :5003   /graphql/* → :5005
```

---

## Service Endpoints

| Service | Port | Health Endpoint |
|---------|------|-----------------|
| API Gateway | 8080 | http://localhost:8080/ |
| Auth Service | 5001 | http://localhost:5001/health |
| Catalog Service | 5002 | http://localhost:5002/ |
| Payment Service | 5003 | http://localhost:5003/health |
| Order Service | 5004 | http://localhost:5004/health |
| GraphQL Gateway | 5005 | http://localhost:5005/ |
| Notification Service | 5006 | http://localhost:5006/health |

---

## Monitoring & Infrastructure

| Service | Port | URL |
|---------|------|-----|
| Grafana | 3000 | http://localhost:3000 |
| Prometheus | 9090 | http://localhost:9090 |
| RabbitMQ Management | 15672 | http://localhost:15672 |
| Consul | 8500 | http://localhost:8500 |
| Jaeger | 16686 | http://localhost:16686 |

---

## Test Data Created

**New User Registered:**
- Email: `test_20260122030736@example.com`
- User ID: `4`

**Order Created:**
- Order ID: `ORD-2BC8968F`
- User: `2` (user@example.com)
- Items: 2x Laptop @ $1000
- Total: $2000
- Payment: Succeeded via stub gateway

**New Product Added (by Admin):**
- Product ID: `3`
- Name: `Test Product 20260122030736`
- Price: $299.99

---

## How to Run E2E Tests Again

```powershell
# Navigate to project directory
cd c:\Users\Константин\microservices-lab

# Run E2E tests
powershell -ExecutionPolicy Bypass -File .\e2e-test.ps1
```
