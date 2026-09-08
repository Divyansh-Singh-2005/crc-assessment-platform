"""Evidence supporting a control assessment."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import EvidenceStatus, EvidenceType, enum_column

if TYPE_CHECKING:
    from app.models.assessment import ControlAssessment


class Evidence(Base, TimestampMixin):
    """Evidence hangs off the assessment, not the control.

    Evidence is only meaningful as support for a specific test on a specific
    date, which is also what makes evidence expiry detectable.
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("control_assessments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        enum_column(EvidenceType, "evidence_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "evidence_status"), default=EvidenceStatus.VALID, nullable=False
    )
    file_path: Mapped[str | None] = mapped_column(String(400))

    assessment: Mapped["ControlAssessment"] = relationship(back_populates="evidence")

    def __repr__(self) -> str:
        return f"<Evidence {self.evidence_ref} {self.name}>"
