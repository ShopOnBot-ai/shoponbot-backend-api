from datetime import datetime

from pydantic import BaseModel

from app.schemas.cart_items import CartItemResponse


class CartRequest(BaseModel):
    product_id: int
    quantity: int


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    created_at: datetime
    updated_at: datetime