from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.cart import Cart
    from app.models.products import Product
    


class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id"),
        CheckConstraint("quantity >= 1", name="check_cart_item_quantity")
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey(Cart.id), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(Product.id), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cart: Mapped["Cart"] = relationship(
        back_populates="items"
    )
    product: Mapped["Product"] = relationship(
        back_populates="cart_items"
    )


