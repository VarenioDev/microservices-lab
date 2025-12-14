from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI(title="Catalog Service")

# Временное хранилище товаров (в проде - БД)
items_db = []

# Модели данных
class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    created_at: str

# CRUD операции
@app.get("/items", response_model=List[ItemResponse])
async def get_items(category: Optional[str] = None):
    """Получить все товары (с фильтром по категории)"""
    if category:
        filtered_items = [item for item in items_db if item.get("category") == category]
        return filtered_items
    return items_db

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    """Получить товар по ID"""
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate):
    """Создать новый товар"""
    item_id = str(uuid.uuid4())
    new_item = {
        "id": item_id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "category": item.category,
        "created_at": datetime.utcnow().isoformat()
    }
    items_db.append(new_item)
    return new_item

@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: str, item: ItemCreate):
    """Обновить товар"""
    for idx, existing_item in enumerate(items_db):
        if existing_item["id"] == item_id:
            updated_item = {
                "id": item_id,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "created_at": existing_item["created_at"]
            }
            items_db[idx] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    """Удалить товар"""
    for idx, item in enumerate(items_db):
        if item["id"] == item_id:
            deleted_item = items_db.pop(idx)
            return {"message": f"Item '{deleted_item['name']}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")

# Базовые эндпоинты
@app.get("/")
def read_root():
    return {"message": "Catalog Service is working!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)