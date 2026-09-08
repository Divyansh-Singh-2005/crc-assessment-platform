"""Shared FastAPI dependencies for authentication and authorisation."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    # A single generic message for every failure mode. Distinguishing
    # "expired" from "invalid signature" from "unknown user" hands an
    # attacker a free oracle.
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        claims = decode_access_token(token)
    except TokenError:
        raise CREDENTIALS_ERROR from None

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise CREDENTIALS_ERROR from None

    user = db.get(User, user_id)
    # The account is re-checked against the database on every request, so a
    # deactivated user loses access immediately rather than at token expiry.
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_role(*allowed: UserRole) -> Callable[[User], User]:
    """Dependency factory enforcing role membership.

    Authorisation is deny by default: a route without this dependency is
    reachable by any authenticated user, and a route with it admits only the
    roles named explicitly.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return current_user

    return dependency


# Convenience aliases matching the permission model:
#   ADMIN   - full access including user administration
#   ANALYST - create and modify assessment data
#   VIEWER  - read only
require_admin = require_role(UserRole.ADMIN)
require_analyst = require_role(UserRole.ADMIN, UserRole.ANALYST)
require_viewer = require_role(UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER)