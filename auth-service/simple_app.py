from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import jwt
import hashlib
from datetime import datetime, timedelta

app = FastAPI(title="Auth Service")

# Конфигурация
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

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

# Простое хеширование пароля (без bcrypt проблем)
def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

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

def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Эндпоинты
@app.post("/register", status_code=201)
async def register(user: UserRegister):
    try:
        print(f"Registering user: {user.username}")
        
        if user.username in fake_users_db:
            raise HTTPException(status_code=400, detail="Username already registered")
        
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
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        if not verify_password(user.password, user_data["hashed_password"]):
            print("Invalid password")
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
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
async def verify_token_endpoint(username: str = Depends(verify_token)):
    return {"username": username, "valid": True}

@app.get("/me")
async def read_users_me(username: str = Depends(verify_token)):
    user_data = fake_users_db.get(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user_data["username"]}

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