"""Password hashing (bcrypt, used directly) and JWT helpers (PyJWT)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password* (bcrypt truncates input > 72 bytes,
    which the request schema guards against with ``max_length=72``)."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time password check; never raises on malformed hashes."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #
def _encode(user_id: int, token_type: TokenType, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        # Random per-token id: two tokens minted in the same second for the same
        # user still differ, so their stored sha256 hashes are unique.
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Short-lived access token."""
    return _encode(user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int) -> str:
    """Long-lived refresh token."""
    return _encode(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Decode *token* and enforce the expected ``type`` claim.

    Raises ``jwt.PyJWTError`` (e.g. ``ExpiredSignatureError`` /
    ``InvalidTokenError``) on any failure — callers translate to HTTP 401.
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected token type {expected_type!r}")
    return payload


def hash_token(raw: str) -> str:
    """SHA-256 hex digest of a raw refresh token — this is what we store in DB."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
