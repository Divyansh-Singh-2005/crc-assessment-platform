"""Password hashing and JSON Web Token handling.

bcrypt is used directly rather than through passlib: passlib's bcrypt backend
is unmaintained against bcrypt 4.1+ and emits a version-detection warning on
every hash. Calling the library directly is fewer moving parts and no warning.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt hashes at most 72 bytes of input and silently ignores the rest.
# Rejecting longer passwords is safer than truncating them, which would make
# two different passwords authenticate the same account.
BCRYPT_MAX_BYTES = 72

# Cost factor. Higher is slower for both defender and attacker; 12 is the
# common production baseline as of writing.
BCRYPT_ROUNDS = 12


class TokenError(Exception):
    """Raised when a token is absent, malformed, expired or untrusted."""


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password exceeds {BCRYPT_MAX_BYTES} bytes once encoded")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time comparison via bcrypt. Never raises on malformed input."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: int, email: str, role: str) -> str:
    """Issue a short-lived access token.

    The role is embedded so authorisation does not require a database read on
    every request. The trade-off is that a role change only takes effect when
    the current token expires; with a 30 minute lifetime that window is
    acceptable here and is recorded as a limitation in the README.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature and expiry, returning the claims.

    The algorithm is pinned to a single value. Accepting the algorithm named
    in the token header is the classic JWT confusion vulnerability, where an
    attacker downgrades to "none" or swaps RS256 for HS256.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc