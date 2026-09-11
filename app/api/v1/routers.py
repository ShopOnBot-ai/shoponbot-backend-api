from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.v1.endpoints import address, admin, auth, cart, products, upload, user

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(address.router, prefix="/address", tags=["Addresses"])
api_router.include_router(
    admin.router, prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)]
)
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(upload.router, prefix="/uploads", tags=["Upload"])
