from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser
from app.db.database import get_db
from app.models.cart import Cart
from app.models.cart_items import CartItem
from app.models.products import Product
from app.schemas.cart import CartRequest, CartResponse
from app.schemas.cart_items import CartItemResponse
from app.utils.logger import logger

router = APIRouter()


@router.post("/", response_model=CartResponse)
async def cart(
    payload: CartRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_id = current_user.id
        logger.info("User id: %s", user_id)
        product_id = payload.product_id
        logger.info("Product id: %s", product_id)
        requested_quantity = payload.quantity
        logger.info("Requested quantity: %s", requested_quantity)

        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        logger.info("Product: %s", product)

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        if not product.in_stock or product.stock_quantity < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product currently Out of Stock",
            )

        result = await db.execute(select(Cart).where(Cart.user_id == user_id))
        cart = result.scalar_one_or_none()
        logger.info("Cart: %s", cart)

        # create new cart logic
        if cart is None:
            cart = Cart(user_id=user_id)
            db.add(cart)

            await db.flush()

        result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id, CartItem.product_id == product_id
            )
        )
        cart_item = result.scalar_one_or_none()
        logger.info("cart item: %s", cart_item)

        if cart_item is not None:
            final_quantity = cart_item.quantity + requested_quantity
        else:
            final_quantity = requested_quantity

        if final_quantity > product.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Sorry, we only have {product.stock_quantity} "
                    f"units of this product available."
                ),
            )

        if cart_item is not None:
            cart_item.quantity = final_quantity
        else:
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=requested_quantity,
            )
            db.add(cart_item)

        result = await db.execute(
            select(Cart)
            .where(Cart.id == cart.id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        cart = result.scalar_one()
        cart_items = []

        for item in cart.items:
            subtotal = item.product.price * item.quantity
            cart_item_response = CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                subtotal=subtotal,
                product=item.product,
            )
            cart_items.append(cart_item_response)
        return CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            items=cart_items,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create cart")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add product to cart",
        )
