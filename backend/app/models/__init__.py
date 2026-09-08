"""Model package. Importing this registers every table on Base.metadata,
which is what Alembic autogenerate reads."""

from app.models.base import Base, TimestampMixin
from app.models.user import User
from app.models.asset import Asset
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkMapping,
    FrameworkSubcategory,
)
from app.models.control import Control
from app.models.assessment import ControlAssessment
from app.models.evidence import Evidence
from app.models.risk import Risk, RiskControl
from app.models.remediation import Remediation
from app.models.audit import AuditLog

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Asset",
    "Framework",
    "FrameworkFunction",
    "FrameworkCategory",
    "FrameworkSubcategory",
    "FrameworkMapping",
    "Control",
    "ControlAssessment",
    "Evidence",
    "Risk",
    "RiskControl",
    "Remediation",
    "AuditLog",
]
