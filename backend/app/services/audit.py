"""Audit trail writer."""

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import User


def client_ip(request: Request | None) -> str | None:
    """Best-effort source address.

    X-Forwarded-For is only trustworthy behind a proxy that overwrites it.
    From an untrusted client it is attacker-controlled, so it is recorded as
    an indicator rather than treated as identity.
    """
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host if request.client else None


def record(
    db: Session,
    *,
    action: AuditAction,
    entity_type: str,
    description: str,
    entity_id: str | None = None,
    user: User | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> AuditLog:
    """Append an audit entry.

    The acting user's email is denormalised onto the row so the trail stays
    readable after an account is deleted or renamed.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=client_ip(request),
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry