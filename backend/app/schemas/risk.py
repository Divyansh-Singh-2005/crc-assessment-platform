"""Risk register schemas."""

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import RiskCategory, RiskRating, RiskStatus, RiskTreatment
from app.schemas.asset import AssetSummary

RISK_REF_PATTERN = re.compile(r"^RISK-\d{3,4}$")


class RiskBase(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    asset_id: int = Field(gt=0)
    category: RiskCategory
    threat: str = Field(min_length=3, max_length=1000, description="The actor or event")
    vulnerability: str = Field(min_length=3, max_length=1000, description="The weakness exploited")
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    risk_owner: str = Field(min_length=2, max_length=120)
    treatment: RiskTreatment = RiskTreatment.MITIGATE
    due_date: date | None = None
    status: RiskStatus = RiskStatus.OPEN


class RiskCreate(RiskBase):
    """Note what is absent: inherent_score and residual_score.

    Scores are computed server side from likelihood, impact and the assessed
    effectiveness of linked controls. Accepting them from the client would
    let an analyst assert a residual score the evidence does not support,
    which is precisely the failure this platform exists to prevent.
    """

    risk_ref: str = Field(examples=["RISK-001"])

    @field_validator("risk_ref")
    @classmethod
    def validate_ref(cls, value: str) -> str:
        value = value.strip().upper()
        if not RISK_REF_PATTERN.match(value):
            raise ValueError("Risk reference must look like RISK-001")
        return value


class RiskUpdate(BaseModel):
    """Partial update. Scores remain server-computed and are recalculated
    whenever likelihood or impact changes."""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=4000)
    asset_id: int | None = Field(default=None, gt=0)
    category: RiskCategory | None = None
    threat: str | None = Field(default=None, min_length=3, max_length=1000)
    vulnerability: str | None = Field(default=None, min_length=3, max_length=1000)
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    risk_owner: str | None = Field(default=None, min_length=2, max_length=120)
    treatment: RiskTreatment | None = None
    due_date: date | None = None
    status: RiskStatus | None = None


class LinkedControl(BaseModel):
    """A control credited against this risk, with its assessed effectiveness."""

    model_config = ConfigDict(from_attributes=True)

    control_id: int
    control_ref: str
    name: str
    weight: Decimal
    effectiveness: Decimal
    implementation_status: str | None = None
    assessed_on: date | None = None
    contribution: Decimal


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_ref: str
    title: str
    description: str
    category: RiskCategory
    threat: str
    vulnerability: str
    likelihood: int
    impact: int
    inherent_score: int
    inherent_rating: RiskRating
    residual_score: int
    residual_rating: RiskRating
    risk_reduction: int
    residual_calculated_at: datetime | None
    risk_owner: str
    treatment: RiskTreatment
    due_date: date | None
    status: RiskStatus
    asset: AssetSummary
    created_at: datetime
    updated_at: datetime


class RiskDetail(RiskRead):
    """Detail view exposing the full calculation chain.

    The linked controls and the aggregate figure are returned alongside the
    scores so the UI can show how the residual was reached. A risk score a
    client cannot interrogate is a score they cannot be expected to accept.
    """

    aggregate_effectiveness: Decimal
    linked_controls: list[LinkedControl]


class ControlLinkRequest(BaseModel):
    control_id: int = Field(gt=0)
    weight: Decimal = Field(
        default=Decimal("1.00"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="How much of this specific risk the control addresses",
    )