from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
import strawberry
from typing import List, Optional
import httpx
from datetime import datetime

SERVICE_URLS = {
    "auth": "http://auth-service:5000",
    "catalog": "http://catalog-service:5000",
    "order": "http://order-service:5000",
    "payment": "http://payment-service:5000"
}


@strawberry.type
class Product:
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    stock: int
    image_url: Optional[str]
    created_at: str
    updated_at: str


@strawberry.type
class OrderItem:
    product_id: str
    quantity: int
    price: float
    name: str
    
    @strawberry.field
    async def product(self) -> Optional[Product]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{SERVICE_URLS['catalog']}/api/v1/catalog/items/{self.product_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return Product(
                        id=data["id"],
                        name=data["name"],
                        description=data.get("description"),
                        price=data["price"],
                        category=data["category"],
                        stock=data.get("stock", 0),
                        image_url=data.get("image_url"),
                        created_at=data["created_at"],
                        updated_at=data["updated_at"]
                    )
            except Exception:
                pass
        return None


@strawberry.type
class Order:
    id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str
    payment_status: str
    shipping_address: strawberry.Private[dict]
    payment_method: str
    tracking_number: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
    
    @strawberry.field
    def address(self) -> str:
        addr = self.shipping_address
        return f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('country', '')}"


@strawberry.type
class User:
    id: strawberry.ID
    username: str
    email: str
    full_name: Optional[str]
    created_at: str
    updated_at: str
    
    @strawberry.field
    async def orders(self) -> List[Order]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{SERVICE_URLS['order']}/api/v1/orders/user/{self.id}",
                    params={"limit": 100},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    orders = []
                    for order_data in data["orders"]:
                        order_items = [
                            OrderItem(
                                product_id=item["product_id"],
                                quantity=item["quantity"],
                                price=item["price"],
                                name=item["name"]
                            )
                            for item in order_data["items"]
                        ]
                        
                        orders.append(Order(
                            id=order_data["id"],
                            user_id=order_data["user_id"],
                            items=order_items,
                            total_amount=order_data["total_amount"],
                            status=order_data["status"],
                            payment_status=order_data["payment_status"],
                            shipping_address=order_data["shipping_address"],
                            payment_method=order_data["payment_method"],
                            tracking_number=order_data.get("tracking_number"),
                            notes=order_data.get("notes"),
                            created_at=order_data["created_at"],
                            updated_at=order_data["updated_at"]
                        ))
                    return orders
            except Exception as e:
                print(f"Error fetching orders: {e}")
        return []


@strawberry.type
class Query:
    @strawberry.field
    async def user(self, id: str) -> Optional[User]:
        async with httpx.AsyncClient() as client:
            try:
                return User(
                    id=id,
                    username=f"user_{id}",
                    email=f"user{id}@example.com",
                    full_name="Test User",
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat()
                )
            except Exception:
                return None
    
    @strawberry.field
    async def product(self, id: str) -> Optional[Product]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{SERVICE_URLS['catalog']}/api/v1/catalog/items/{id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return Product(
                        id=data["id"],
                        name=data["name"],
                        description=data.get("description"),
                        price=data["price"],
                        category=data["category"],
                        stock=data.get("stock", 0),
                        image_url=data.get("image_url"),
                        created_at=data["created_at"],
                        updated_at=data["updated_at"]
                    )
            except Exception:
                pass
        return None
    
    @strawberry.field
    async def products(
        self,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 20
    ) -> List[Product]:
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "page": 1,
                    "page_size": limit,
                    "category": category,
                    "min_price": min_price,
                    "max_price": max_price,
                    "search": search
                }
                params = {k: v for k, v in params.items() if v is not None}
                
                response = await client.get(
                    f"{SERVICE_URLS['catalog']}/api/v1/catalog/items",
                    params=params,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = []
                    for item in data["items"]:
                        products.append(Product(
                            id=item["id"],
                            name=item["name"],
                            description=item.get("description"),
                            price=item["price"],
                            category=item["category"],
                            stock=item.get("stock", 0),
                            image_url=item.get("image_url"),
                            created_at=item["created_at"],
                            updated_at=item["updated_at"]
                        ))
                    return products
            except Exception as e:
                print(f"Error fetching products: {e}")
        return []
    
    @strawberry.field
    async def user_orders(self, user_id: str) -> List[Order]:
        async with httpx.AsyncClient() as client:
            try:
                orders_response = await client.get(
                    f"{SERVICE_URLS['order']}/api/v1/orders/user/{user_id}",
                    params={"limit": 50},
                    timeout=5.0
                )
                
                if orders_response.status_code == 200:
                    data = orders_response.json()
                    orders = []
                    
                    for order_data in data["orders"]:
                        order_items = []
                        
                        for item in order_data["items"]:
                            order_items.append(OrderItem(
                                product_id=item["product_id"],
                                quantity=item["quantity"],
                                price=item["price"],
                                name=item["name"]
                            ))
                        
                        order = Order(
                            id=order_data["id"],
                            user_id=order_data["user_id"],
                            items=order_items,
                            total_amount=order_data["total_amount"],
                            status=order_data["status"],
                            payment_status=order_data["payment_status"],
                            shipping_address=order_data["shipping_address"],
                            payment_method=order_data["payment_method"],
                            tracking_number=order_data.get("tracking_number"),
                            notes=order_data.get("notes"),
                            created_at=order_data["created_at"],
                            updated_at=order_data["updated_at"]
                        )
                        
                        orders.append(order)
                    
                    return orders
            except Exception as e:
                print(f"Error fetching user orders: {e}")
        
        return []
    
    @strawberry.field
    async def order(self, id: str) -> Optional[Order]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{SERVICE_URLS['order']}/api/v1/orders/{id}",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    order_data = response.json()
                    
                    order_items = [
                        OrderItem(
                            product_id=item["product_id"],
                            quantity=item["quantity"],
                            price=item["price"],
                            name=item["name"]
                        )
                        for item in order_data["items"]
                    ]
                    
                    return Order(
                        id=order_data["id"],
                        user_id=order_data["user_id"],
                        items=order_items,
                        total_amount=order_data["total_amount"],
                        status=order_data["status"],
                        payment_status=order_data["payment_status"],
                        shipping_address=order_data["shipping_address"],
                        payment_method=order_data["payment_method"],
                        tracking_number=order_data.get("tracking_number"),
                        notes=order_data.get("notes"),
                        created_at=order_data["created_at"],
                        updated_at=order_data["updated_at"]
                    )
            except Exception as e:
                print(f"Error fetching order: {e}")
        
        return None


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_order(
        self,
        user_id: str,
        items: List[strawberry.scalars.JSON],
        shipping_address: strawberry.scalars.JSON
    ) -> Optional[Order]:
        async with httpx.AsyncClient() as client:
            try:
                order_data = {
                    "user_id": user_id,
                    "items": items,
                    "shipping_address": shipping_address,
                    "payment_method": "card"
                }
                
                response = await client.post(
                    f"{SERVICE_URLS['order']}/api/v1/orders",
                    json=order_data,
                    timeout=10.0
                )
                
                if response.status_code == 201:
                    order_data = response.json()
                    
                    order_items = [
                        OrderItem(
                            product_id=item["product_id"],
                            quantity=item["quantity"],
                            price=item["price"],
                            name=item["name"]
                        )
                        for item in order_data["items"]
                    ]
                    
                    return Order(
                        id=order_data["id"],
                        user_id=order_data["user_id"],
                        items=order_items,
                        total_amount=order_data["total_amount"],
                        status=order_data["status"],
                        payment_status=order_data["payment_status"],
                        shipping_address=order_data["shipping_address"],
                        payment_method=order_data["payment_method"],
                        tracking_number=order_data.get("tracking_number"),
                        notes=order_data.get("notes"),
                        created_at=order_data["created_at"],
                        updated_at=order_data["updated_at"]
                    )
            except Exception as e:
                print(f"Error creating order: {e}")
        
        return None


schema = strawberry.Schema(query=Query, mutation=Mutation)

app = FastAPI(
    title="GraphQL Gateway",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphql_app = GraphQLRouter(schema, graphiql=True)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "graphql-gateway",
        "graphql_endpoint": "/graphql",
        "graphiql": "/graphql"
    }


@app.get("/")
async def root():
    return {
        "message": "GraphQL Gateway",
        "endpoints": {
            "graphql": "/graphql",
            "graphiql": "/graphql",
            "health": "/health"
        },
        "integrated_services": list(SERVICE_URLS.keys())
    }
