from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminProductCreateRequest(BaseModel):
    title: str = Field(max_length=100, min_length=1)
    description: str = Field(max_length=250, min_length=1)
    image_url: str | None = None
    price: int
    in_stock: bool
    stock_quantity: int


class AdminProductUpdateRequest(BaseModel):
    title: str = Field(max_length=100, min_length=1)
    description: str = Field(max_length=250, min_length=1)
    image_url: str | None = None
    price: int
    in_stock: bool
    stock_quantity: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    image_url: str | None
    price: int
    in_stock: bool
    stock_quantity: int
    created_at: datetime


class AdminProductCreateResponse(BaseModel):
    message: str
    product: ProductResponse


class AdminProductsResponse(BaseModel):
    message: str
    products: list[ProductResponse]


class AdminProductUpdateResponse(BaseModel):
    message: str
    product: ProductResponse


class AdminProductDeleteResponse(BaseModel):
    message: str
    product_id: int


class PublicProductsResponse(BaseModel):
    model_config = ConfigDict(from_attributes= True)
    id: int
    title: str
    description: str
    image_url: str | None
    price: int
    in_stock: bool
    created_at: datetime


class ProductsResponse(BaseModel):
    message: str
    products: list[PublicProductsResponse]
    hasMore: bool
    page: int
    limit: int