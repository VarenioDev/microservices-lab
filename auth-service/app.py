from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import time
from datetime import datetime, timedelta
import bcrypt
from typing import Dict

from models import UserCreate, UserResponse, Role, Token

app = FastAPI()
security = HTTPBearer()

# Улучшенная "БД" пользователей (в реальном проекте - база данных)
users_db: Dict[str, dict] = {
    "admin@example.com": {
        "id": "1",
        "email": "admin@example.com",
        "hashed_password": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
        "full_name": "Admin User",
        "role": Role.ADMIN,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00"
    },
    "user@example.com": {
        "id": "2",
        "email": "user@example.com",
        "hashed_password": bcrypt.hashpw("user123".encode(), bcrypt.gensalt()).decode(),
        "full_name": "Regular User",
        "role": Role.USER,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00"
    }
}

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class LoginRequest(BaseModel):
    email: str
    password: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/register")
async def register(user_data: UserCreate):
    """Регистрация нового пользователя"""
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt())
    user_id = str(len(users_db) + 1)
    
    users_db[user_data.email] = {
        "id": user_id,
        "email": user_data.email,
        "hashed_password": hashed_password.decode(),
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )

@app.post("/login")
async def login(login_data: LoginRequest):
    """Логин - возвращает JWT токен"""
    user = users_db.get(login_data.email)
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["email"],
            "user_id": user["id"],
            "role": user["role"],
            "email": user["email"]
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        role=user["role"],
        user_id=user["id"]
    )

@app.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка токена - используется nginx auth_request"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        user_id = payload.get("user_id")
        
        if email not in users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Создаем ответ с заголовками для nginx
        from fastapi.responses import JSONResponse
        response = JSONResponse({
            "valid": True,
            "user": email,
            "user_id": user_id,
            "role": role
        })
        
        # Устанавливаем заголовки для nginx
        response.headers["X-Auth-User"] = email
        response.headers["X-Auth-Role"] = role
        response.headers["X-Auth-User-Id"] = user_id
        
        return response
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/users/me")
async def read_users_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получить информацию о текущем пользователе"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = users_db.get(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"]
        )
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
def health():
    return {"status": "ok"}