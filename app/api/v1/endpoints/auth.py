import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cookies import set_auth_cookie
from app.core.redis import check_and_set_cooldown, set_otp, verify_and_delete_otp
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.db.database import get_db
from app.messaging.publisher import publish_email_task
from app.models.user import User
from app.schemas.auth import LoginResponse, OTPRequest, OTPVerify

router = APIRouter()

logger = logging.getLogger("uvicorn.error")


@router.post("/request_otp", status_code=status.HTTP_200_OK)
async def request_otp(payload: OTPRequest):
    email = payload.email.lower()

    # protect from spammers (later will implement more security like fetch users current IP address using Nginx)
    allowed = await check_and_set_cooldown(email, seconds=30)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait 30 seconds before requesting another OTP.",
        )

    generate_otp = f"{secrets.randbelow(1000000):06d}"

    # Temporary set this OTP to redis with 5 minutes of expiration time  because we no lone needed this otp like setting it to database.
    await set_otp(email, code=generate_otp)

    # send OTP to mail (using Resend) -> used previouly, now it has been moved inside email_worker(rabbitmq)
    await publish_email_task(email=email, otp=generate_otp)

    return {"message": "OTP sent successfully to your email"}


@router.post(
    "/verify_otp", response_model=LoginResponse, status_code=status.HTTP_200_OK
)
async def verify_otp(
    payload: OTPVerify, response: Response, db: Annotated[AsyncSession, Depends(get_db)]
):
    email = payload.email.lower()
    otp = payload.otp

    # Check OTP have already expired or not
    is_valid = await verify_and_delete_otp(email=email, input_code=otp)
    logger.info("is_valid: %s", is_valid)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid and expired OTP"
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    is_new_user = False

    if not user:
        user = User(email=email, is_active=True)
        db.add(user)
        is_new_user = True

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or suspended",
        )

    user.last_login = datetime.now(UTC)
    await db.flush()
    await db.refresh(user)

    # Create access and refresh token and set it to HttpOnly cookie for security and industry purpose
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role}, expires_delta=refresh_token_expires
    )
    set_auth_cookie(
        response=response,
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
    )
    set_auth_cookie(
        response=response,
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )
    return LoginResponse(is_new_user=is_new_user, user=user)


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]
):
    refresh_cookie = request.cookies.get("refresh_token")

    # for 7 days
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    # get user_id from token as sub
    user_id = verify_token(token=refresh_cookie, expected_type="refresh")
    if user_id.get("user_id") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    try:
        user_id_int = int(user_id.get("user_id"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalars().first()
    logger.info("user object: %s", user)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive or suspended user account",
        )

    # Regenrate the access token based on the refresh token because access token expires in 30 minutes and users will not need to login  again and again after every 30 minutes 
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}, expires_delta=access_token_expires
    )
    set_auth_cookie(
        response=response,
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return {"message": "Access token refreshed"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")

    return {"message": "Logout successfully"}
