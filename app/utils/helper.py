from app.models.cart import Cart
from app.schemas.cart import CartResponse
from app.schemas.cart_items import CartItemResponse
from app.utils.logger import logger


def _prepare_cart_response(cart: Cart) -> CartResponse:
    """Calculates subtotals and converts Cart ORM model into CartResponse Pydantic schema."""
    cart_items = []
    
    for item in cart.items:
        logger.info(
            "CartItem: id=%s, product_id=%s, quantity=%s, product=%s",
            item.id,
            item.product_id,
            item.quantity,
            item.product.title,
        )
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