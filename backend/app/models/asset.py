"""Organisational assets under assessment."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import AssetType, DataClassification, Environment, enum_column

if TYPE_CHECKING:
    from app.models.risk import Risk


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("criticality BETWEEN 1 AND 5", name="ck_assets_criticality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(enum_column(AssetType, "asset_type"), nullable=False)
    business_owner: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[Environment] = mapped_column(enum_column(Environment, "environment"), nullable=False)
    data_classification: Mapped[DataClassification] = mapped_column(
        enum_column(DataClassification, "data_classification"), nullable=False
    )
    criticality: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    risks: Mapped[list["Risk"]] = relationship(back_populates="asset")

    def __repr__(self) -> str:
        return f"<Asset {self.asset_ref} {self.name}>"
