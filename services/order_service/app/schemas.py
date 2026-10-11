from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Status = Literal['CREATED','CONFIRMED','SHIPPED','DELIVERED','CANCELLED']
def cents(value: Decimal) -> int:
    return int((value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100))
def money(value: int) -> Decimal:
    return (Decimal(value) / 100).quantize(Decimal('0.01'))
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

class ItemIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=10000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal('0.00'), ge=0, max_digits=12, decimal_places=2)
    @model_validator(mode='after')
    def discount_valid(self):
        if cents(self.discount_amount) > cents(self.unit_price) * self.quantity:
            raise ValueError('discount cannot exceed the extended item price')
        return self

class OrderCreate(BaseModel):
    order_id: str | None = Field(default=None, min_length=1, max_length=80)
    customer_id: str = Field(min_length=1, max_length=80)
    order_status: Status = 'CREATED'
    order_timestamp: datetime | None = None
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$')
    items: list[ItemIn] = Field(min_length=1)
    @field_validator('order_timestamp')
    @classmethod
    def timezone_required(cls, value):
        if value and value.tzinfo is None: raise ValueError('timestamp must include a timezone')
        return value

class OrderPatch(BaseModel):
    order_status: Status

class ItemOut(BaseModel):
    order_item_id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    line_total: Decimal

class OrderOut(BaseModel):
    order_id: str
    customer_id: str
    order_status: str
    order_timestamp: str
    currency: str
    order_total: Decimal
    created_at: str
    updated_at: str
    source_version: int
    items: list[ItemOut]

class OrderPage(BaseModel):
    items: list[OrderOut]
    limit: int
    offset: int
