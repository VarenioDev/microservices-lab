from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"

# Заменяем EmailStr на обычную строку с валидацией через Field
class UserBase(BaseModel):
    email: str = Field(..., description="Email пользователя", pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    role: Role = Role.USER

class UserInDB(UserBase):
    id: str
    hashed_password: str
    role: Role
    created_at: str
    last_login: Optional[str] = None

class UserResponse(UserBase):
    id: str
    role: Role

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: Role
    user_id: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[Role] = None
    scopes: List[str] = []

class Permission(str, Enum):
    READ_CATALOG = "read:catalog"
    WRITE_CATALOG = "write:catalog"
    DELETE_CATALOG = "delete:catalog"
    READ_ORDERS = "read:orders"
    WRITE_ORDERS = "write:orders"
    MANAGE_USERS = "manage:users"
    PROCESS_PAYMENTS = "process:payments"

# Ролевые разрешения
ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.READ_CATALOG,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
    ],
    Role.ADMIN: [
        Permission.READ_CATALOG,
        Permission.WRITE_CATALOG,
        Permission.DELETE_CATALOG,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
        Permission.MANAGE_USERS,
        Permission.PROCESS_PAYMENTS,
    ],
    Role.MANAGER: [
        Permission.READ_CATALOG,
        Permission.WRITE_CATALOG,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
        Permission.PROCESS_PAYMENTS,
    ]
}