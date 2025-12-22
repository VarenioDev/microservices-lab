from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI()

# Модель товара
class Product(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None
    in_stock: bool = True

class ProductCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

# Простые товары
products = [
    Product(id=1, name="Laptop", price=1000, description="Gaming laptop", in_stock=True),
    Product(id=2, name="Phone", price=500, description="Smartphone", in_stock=True)
]

def verify_admin_role(x_user_role: str = Header(...)):
    """Зависимость для проверки роли администратора"""
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return x_user_role

def get_current_user_id(x_user_id: str = Header(...)):
    """Зависимость для получения ID пользователя"""
    return x_user_id

@app.get("/")
def home():
    return {"message": "Catalog Service"}

@app.get("/products")
def get_products():
    """Получить все товары - доступно всем аутентифицированным пользователям"""
    return {"products": products}

@app.get("/products/{product_id}")
def get_product(product_id: int):
    """Получить товар по ID"""
    for product in products:
        if product.id == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.post("/products")
def create_product(
    product: ProductCreate,
    role: str = Depends(verify_admin_role),
    user_id: str = Depends(get_current_user_id)
):
    """Создать товар - только для админов"""
    new_id = max(p.id for p in products) + 1 if products else 1
    new_product = Product(
        id=new_id,
        name=product.name,
        price=product.price,
        description=product.description
    )
    products.append(new_product)
    return {"message": "Product created", "product": new_product, "created_by": user_id}

@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    product: ProductCreate,
    role: str = Depends(verify_admin_role),
    user_id: str = Depends(get_current_user_id)
):
    """Обновить товар - только для админов"""
    for i, p in enumerate(products):
        if p.id == product_id:
            updated_product = Product(
                id=product_id,
                name=product.name,
                price=product.price,
                description=product.description,
                in_stock=p.in_stock
            )
            products[i] = updated_product
            return {"message": "Product updated", "product": updated_product, "updated_by": user_id}
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    role: str = Depends(verify_admin_role),
    user_id: str = Depends(get_current_user_id)
):
    """Удалить товар - только для админов"""
    global products
    initial_length = len(products)
    products = [p for p in products if p.id != product_id]
    
    if len(products) == initial_length:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted", "deleted_by": user_id}

@app.get("/health")
def health():
    return {"status": "ok"}