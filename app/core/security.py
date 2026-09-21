# JWT creation, decoding, password hashing (if any)
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            days=settings.refresh_token_expire_days,
        )
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt

# JWT has a 3 parts (Header: { "alg":"HS256", "typ":"JWT" }, payload: { "sub":"15", "iat":..., "exp":... }, signature: MACSHA256( Header + payload + secret key))

def verify_token(token: str, expected_type: str) -> dict | None:
    """Verify a JWT access token and return the subject (user id) if valid."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    else:
        if payload.get("type") != expected_type:
            return None
        return {
            "user_id": int(payload.get("sub")),
            "role": payload.get("role")
        }