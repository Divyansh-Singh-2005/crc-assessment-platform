"""Point-in-time control assessments."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ImplementationStatus, enum_column

if TYPE_CHECKING:
    from app.models.control import Control
    from app.models.evidence import Evidence
    from app.models.user import User


class ControlAssessment(Base, TimestampMixin):
    """One test of one control on one date.

    Rows are append-only. Re-testing a control creates a new assessment rather
    than editing the previous one, so the control has a defensible history.
    """

    __tablename__ = "control_assessments"
    __table_args__ = (
        CheckConstraint("effectiveness >= 0 AND effectiveness <= 1", name="ck_assessments_effectiveness"),
        Index("ix_assessments_control_date", "control_id", "assessment_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    assessor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        enum_column(ImplementationStatus, "implementation_status"), nullable=False
    )
    effectiveness: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    findings: Mapped[str | None] = mapped_column(Text)
    tester_comments: Mapped[str | None] = mapped_column(Text)
    remediation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    control: Mapped["Control"] = relationship(back_populates="assessments")
    assessor: Mapped["User | None"] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ControlAssessment {self.assessment_ref} {self.implementation_status}>"
