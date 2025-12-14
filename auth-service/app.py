from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import hashlib

app = FastAPI(title="Auth Service")

# Конфигурация
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Используем bcrypt с автоматическим хешированием длинных паролей
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__max_password_length=128  # Увеличиваем лимит
)

# Временная "база данных"
fake_users_db = {}

# Модели данных
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Функция для безопасного хеширования пароля (обходит ограничение 72 байта)
def get_password_hash(password):
    # Если пароль слишком длинный, сначала хешируем его через SHA-256
    if len(password.encode('utf-8')) > 72:
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    # Аналогично для проверки
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)

# Функции для JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Эндпоинты
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    try:
        print(f"Registering user: {user.username}")
        
        if user.username in fake_users_db:
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )
        
        hashed_password = get_password_hash(user.password)
        fake_users_db[user.username] = {
            "username": user.username,
            "hashed_password": hashed_password
        }
        
        print(f"User {user.username} registered successfully")
        return {"message": "User registered successfully"}
        
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    try:
        print(f"Login attempt for user: {user.username}")
        
        user_data = fake_users_db.get(user.username)
        if not user_data:
            print("User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        if not verify_password(user.password, user_data["hashed_password"]):
            print("Invalid password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        print(f"Login successful for {user.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify")
async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=400, detail="Invalid token")
        return {"username": username, "valid": True}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

# Базовые эндпоинты
@app.get("/")
def read_root():
    return {"message": "Auth Service is working!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")