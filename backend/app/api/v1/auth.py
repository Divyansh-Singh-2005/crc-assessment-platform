"""Authentication and user administration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead
from app.services import audit

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Exchange credentials for an access token.

    Uses the OAuth2 password form so the Swagger Authorise button works
    against this endpoint directly.
    """
    user = db.scalar(select(User).where(User.email == form.username))

    # Both branches return the same 401. Confirming that an email exists is a
    # user-enumeration weakness, which matters most on a login endpoint.
    if user is None or not verify_password(form.password, user.password_hash):
        audit.record(
            db,
            action=AuditAction.LOGIN_FAILED,
            entity_type="User",
            entity_id=form.username[:40],
            description="Failed authentication attempt",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    audit.record(
        db,
        action=AuditAction.LOGIN,
        entity_type="User",
        entity_id=str(user.id),
        description=f"Successful authentication for {user.email}",
        user=user,
        request=request,
    )

    return Token(
        access_token=create_access_token(
            user_id=user.id, email=user.email, role=user.role.value
        ),
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's own profile."""
    return current_user


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    """List all accounts. Administrator only."""
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    """Create an account. Administrator only."""
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()

    audit.record(
        db,
        action=AuditAction.CREATE,
        entity_type="User",
        entity_id=str(user.id),
        description=f"Created account {user.email} with role {user.role.value}",
        user=current_user,
        request=request,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user