"""Append-only audit trail."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import AuditAction, enum_column


class AuditLog(Base):
    """Records state-changing actions.

    user_id has no foreign key and the acting email is denormalised on purpose:
    an audit trail must stay readable and intact even if the user record is
    later removed. Rows are never updated or deleted by the application.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_timestamp", "timestamp"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[AuditAction] = mapped_column(enum_column(AuditAction, "audit_action"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type} {self.entity_id}>"
