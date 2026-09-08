"""Remediation actions arising from control gaps."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RemediationPriority, RemediationStatus, enum_column


class Remediation(Base, TimestampMixin):
    """A tracked action. Gaps themselves are derived at read time, but a
    remediation has an owner and a due date, so it must persist."""

    __tablename__ = "remediations"

    id: Mapped[int] = mapped_column(primary_key=True)
    remediation_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    control_id: Mapped[int | None] = mapped_column(
        ForeignKey("controls.id", ondelete="SET NULL"), index=True
    )
    risk_id: Mapped[int | None] = mapped_column(
        ForeignKey("risks.id", ondelete="SET NULL"), index=True
    )
    priority: Mapped[RemediationPriority] = mapped_column(
        enum_column(RemediationPriority, "remediation_priority"), index=True, nullable=False
    )
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RemediationStatus] = mapped_column(
        enum_column(RemediationStatus, "remediation_status"),
        default=RemediationStatus.OPEN,
        nullable=False,
    )
    estimated_effort_days: Mapped[int | None] = mapped_column(Integer)

    control = relationship("Control")
    risk = relationship("Risk")

    def __repr__(self) -> str:
        return f"<Remediation {self.remediation_ref} {self.priority} {self.status}>"
