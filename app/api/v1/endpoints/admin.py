from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import build_admin_product_cache_key, redis_client
from app.db.database import get_db
from app.models.products import Product
from app.models.user import User
from app.schemas.products import (
    AdminProductCreateRequest,
    AdminProductCreateResponse,
    AdminProductDeleteResponse,
    AdminProductsResponse,
    AdminProductUpdateRequest,
    AdminProductUpdateResponse,
    ProductResponse,
)
from app.schemas.user import (
    UserActionStatusRequest,
    UserActionStatusResponse,
    UserResponse,
)
from app.services.aws_service import delete_from_s3, generate_signed_url
from app.utils.logger import logger

router = APIRouter()


@router.get("/test")
async def test_admin():
    return {
        "message": "Admin access granted",
    }


@router.get("/users", response_model=UserResponse)
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
):
    offset = (page - 1) * limit
    query = select(User)

    if search:
        query = query.where(
            or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%"))
        )

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    query = query.offset(offset).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return {"users": users, "page": page, "limit": limit, "total_count": total_count}


@router.post("/user/deactivate", response_model=UserActionStatusResponse)
async def deactivate_user(
    request: UserActionStatusRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    user_id = request.id

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    print(user, "userId")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    user.is_active = False

    response = UserActionStatusResponse(
        message="User account successfully deactivated", user=user
    )
    return response


@router.post("/user/activate", response_model=UserActionStatusResponse)
async def activate_user(
    request: UserActionStatusRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    user_id = request.id

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    user.is_active = True

    response = UserActionStatusResponse(
        message="User account successfully activated", user=user
    )

    return response


@router.get("/products", response_model=AdminProductsResponse)
async def get_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
):
    offset = (page - 1) * limit
    cache_key = build_admin_product_cache_key(page, limit, search)
    cached_data = await redis_client.get(cache_key)

    if cached_data is not None:
        return AdminProductsResponse.model_validate_json(cached_data)

    query = select(Product)

    if search:
        query = query.where(Product.title.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_products = count_result.scalar_one()

    query = query.offset(offset).limit(limit).order_by(Product.created_at.desc(), Product.id.desc())
    result = await db.execute(query)
    products = result.scalars().all()

    response_products = []

    for product in products:
        response_products.append(
            ProductResponse(
                id=product.id,
                title=product.title,
                description=product.description,
                image_url=generate_signed_url(product.image_url),
                price=product.price,
                in_stock=product.in_stock,
                stock_quantity=product.stock_quantity,
                created_at=product.created_at,
            )
        )

    response = AdminProductsResponse(
        message="Products fetched successfully",
        products=response_products,
        page=page,
        limit=limit,
        total_count=total_products,
    )
    response_json = response.model_dump_json()
    await redis_client.set(cache_key, response_json, ex=60)

    return response


@router.post("/add_product", response_model=AdminProductCreateResponse)
async def create_product(
    payload: AdminProductCreateRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        product = Product(
            title=payload.title,
            description=payload.description,
            image_url=payload.image_url,
            price=payload.price,
            in_stock=payload.in_stock,
            stock_quantity=payload.stock_quantity,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)
        response = AdminProductCreateResponse(
            message="Product created successfully", product=product
        )
        return response
    except Exception:
        logger.exception("Failed to create product..")
        raise


@router.patch("/products/{product_id}", response_model=AdminProductUpdateResponse)
async def update_product(
    product_id: int,
    payload: AdminProductUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().one_or_none()
        logger.info(product, "product")

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.."
            )

        product.title = payload.title
        product.description = payload.description
        product.image_url = payload.image_url
        product.price = payload.price
        product.in_stock = payload.in_stock
        product.stock_quantity = payload.stock_quantity

        await db.flush()
        await db.refresh(product)
        response = AdminProductUpdateResponse(
            message="Product updated successfully", product=product
        )
        return response
    except Exception:
        logger.exception("Failed to update product")
        raise


@router.delete("/products/{product_id}", response_model=AdminProductDeleteResponse)
async def delete_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.."
            )

        object_key = product.image_url

        await db.delete(product)

        if object_key:
            background_tasks.add_task(delete_from_s3, object_key)
        return AdminProductDeleteResponse(
            message="Product deleted successfully", product_id=product.id
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Faild to delete product")
        raise
