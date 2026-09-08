"""Risk register entries and their links to mitigating controls."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RiskCategory, RiskStatus, RiskTreatment, enum_column

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.control import Control


class RiskControl(Base):
    """Association object linking a risk to a control that mitigates it.

    The weight expresses how much of THIS risk the control actually addresses.
    A control can be strong in general and only partially relevant here.
    """

    __tablename__ = "risk_controls"
    __table_args__ = (
        CheckConstraint("weight >= 0 AND weight <= 1", name="ck_risk_controls_weight"),
    )

    risk_id: Mapped[int] = mapped_column(
        ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True
    )
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("1.00"), nullable=False)

    risk: Mapped["Risk"] = relationship(back_populates="control_links")
    control: Mapped["Control"] = relationship(back_populates="risk_links")


class Risk(Base, TimestampMixin):
    """A risk. Scores are persisted snapshots produced by services.scoring.

    Ratings (Low/Medium/High/Critical) are deliberately NOT stored. They are
    derived from the scores in one place so the bands cannot drift.
    """

    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("likelihood BETWEEN 1 AND 5", name="ck_risks_likelihood"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="ck_risks_impact"),
        Index("ix_risks_residual_score", "residual_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    category: Mapped[RiskCategory] = mapped_column(
        enum_column(RiskCategory, "risk_category"), index=True, nullable=False
    )
    threat: Mapped[str] = mapped_column(Text, nullable=False)
    vulnerability: Mapped[str] = mapped_column(Text, nullable=False)

    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    inherent_score: Mapped[int] = mapped_column(Integer, nullable=False)
    residual_score: Mapped[int] = mapped_column(Integer, nullable=False)
    residual_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    risk_owner: Mapped[str] = mapped_column(String(120), nullable=False)
    treatment: Mapped[RiskTreatment] = mapped_column(
        enum_column(RiskTreatment, "risk_treatment"), default=RiskTreatment.MITIGATE, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RiskStatus] = mapped_column(
        enum_column(RiskStatus, "risk_status"), default=RiskStatus.OPEN, nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="risks")
    control_links: Mapped[list["RiskControl"]] = relationship(
        back_populates="risk", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Risk {self.risk_ref} inherent={self.inherent_score} residual={self.residual_score}>"
