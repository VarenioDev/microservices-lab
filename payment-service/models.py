from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class PaymentMethod(str, Enum):
    CARD = "card"
    YOOMONEY = "yoomoney"
    SBP = "sbp"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class PaymentCreate(BaseModel):
    order_id: str = Field(...)
    user_id: str = Field(...)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="RUB")
    payment_method: PaymentMethod = Field(...)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    payment_url: Optional[str]
    amount: float
    currency: str
    order_id: str
