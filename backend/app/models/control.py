"""Security controls in the organisational control library."""

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ControlType, TestingFrequency, enum_column

if TYPE_CHECKING:
    from app.models.assessment import ControlAssessment
    from app.models.framework import FrameworkMapping
    from app.models.risk import RiskControl


class Control(Base, TimestampMixin):
    """A control definition.

    Note that the NIST function and category are not stored here as text.
    They are reached through framework_mappings, so a control can satisfy
    several subcategories and coverage can be computed rather than typed in.
    """

    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    control_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    control_type: Mapped[ControlType] = mapped_column(
        enum_column(ControlType, "control_type"), nullable=False
    )
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    testing_frequency: Mapped[TestingFrequency] = mapped_column(
        enum_column(TestingFrequency, "testing_frequency"), nullable=False
    )

    assessments: Mapped[list["ControlAssessment"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )
    framework_mappings: Mapped[list["FrameworkMapping"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list["RiskControl"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Control {self.control_ref} {self.name}>"
