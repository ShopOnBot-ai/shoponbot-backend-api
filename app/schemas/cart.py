from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.cart_items import CartItemResponse


class CartRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1)


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: list[CartItemResponse]
    created_at: datetime
    updated_at: datetime