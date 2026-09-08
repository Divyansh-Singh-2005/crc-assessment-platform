"""Asset inventory schemas."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AssetType, DataClassification, Environment

ASSET_REF_PATTERN = re.compile(r"^ASSET-\d{3,4}$")


class AssetBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    asset_type: AssetType
    business_owner: str = Field(min_length=2, max_length=120)
    environment: Environment
    data_classification: DataClassification
    criticality: int = Field(ge=1, le=5, description="1 = minimal, 5 = business critical")
    description: str | None = Field(default=None, max_length=2000)


class AssetCreate(AssetBase):
    asset_ref: str = Field(examples=["ASSET-001"])

    @field_validator("asset_ref")
    @classmethod
    def validate_ref(cls, value: str) -> str:
        """Enforce a consistent reference format.

        Analysts cite these references in reports and remediation tickets, so
        an unconstrained free-text identifier degrades into ASSET1, asset-01
        and A001 within a week.
        """
        value = value.strip().upper()
        if not ASSET_REF_PATTERN.match(value):
            raise ValueError("Asset reference must look like ASSET-001")
        return value


class AssetUpdate(BaseModel):
    """Partial update. Every field optional; asset_ref is deliberately absent,
    since a reference cited in an issued report must not be rewritten."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    asset_type: AssetType | None = None
    business_owner: str | None = Field(default=None, min_length=2, max_length=120)
    environment: Environment | None = None
    data_classification: DataClassification | None = None
    criticality: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, max_length=2000)


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_ref: str
    created_at: datetime
    updated_at: datetime


class AssetSummary(BaseModel):
    """Compact form for embedding inside risk responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_ref: str
    name: str
    criticality: int