from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.products import Product
from app.schemas.products import ProductsResponse, PublicProductsResponse
from app.services.aws_service import generate_signed_url
from app.utils.logger import logger

router = APIRouter()


@router.get("/", response_model=ProductsResponse)
async def get_all_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 10,
    page: int = 1,
    search: str | None = None,
):
    offset = (page - 1) * limit
    query = select(Product)
    try:
        if search:
            query = query.where(Product.title.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_products = count_result.scalar_one()

        query = query.offset(offset).limit(limit).order_by(Product.created_at.desc())
        result = await db.execute(query)
        products = result.scalars().all()

        has_more = offset + len(products) < total_products
        logger.info(has_more, "hasmore")

        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No products found."
            )

        response_products = []

        for product in products:
            response_products.append(
                PublicProductsResponse(
                    id=product.id,
                    title=product.title,
                    description=product.description,
                    image_url=generate_signed_url(product.image_url),
                    price=product.price,
                    in_stock=product.in_stock,
                    created_at=product.created_at,
                )
            )

        response = ProductsResponse(
            message="Fetched products successfully",
            products=response_products,
            hasMore=has_more,
            page=page,
            limit=limit
        )
        return response
    except Exception:
        logger.exception("Failed to fetch products")
        raise
