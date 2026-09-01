from pydantic import BaseModel, ConfigDict


class CartProduct(BaseModel):
    model_config = ConfigDict(from_attributes= True)
    
    title: str
    description: str | None = None
    price: int
    image_url: str | None = None

class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes= True)

    id: int
    product_id: int
    quantity: int
    product: CartProduct
    subtotal: int