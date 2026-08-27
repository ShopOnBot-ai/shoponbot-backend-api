from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.cart_items import CartItem
from app.models.user import User


class Cart(Base):
    __tablename__ = "cart"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False, index=True)

    user: Mapped["User"] = relationship(
        back_populates="cart"
    )
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart"
    )
