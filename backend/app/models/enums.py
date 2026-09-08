"""Domain enumerations shared by the ORM models and the API schemas."""

from enum import Enum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[Enum], name: str) -> SAEnum:
    """Persist enums as VARCHAR plus a CHECK constraint.

    Native PostgreSQL enum types require ALTER TYPE gymnastics in migrations
    whenever a value is added. A checked VARCHAR gives the same integrity
    guarantee with far simpler schema evolution, and stores readable values.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=64,
        values_callable=lambda members: [member.value for member in members],
    )


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class AssetType(str, Enum):
    APPLICATION = "Application"
    DATABASE = "Database"
    CLOUD_ENVIRONMENT = "Cloud Environment"
    NETWORK = "Network"
    ENDPOINT = "Endpoint"
    THIRD_PARTY_SERVICE = "Third-Party Service"


class Environment(str, Enum):
    PRODUCTION = "Production"
    STAGING = "Staging"
    DEVELOPMENT = "Development"


class DataClassification(str, Enum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"


class RiskCategory(str, Enum):
    IAM = "Identity & Access Management"
    DATA_PROTECTION = "Data Protection"
    CLOUD_SECURITY = "Cloud Security"
    APPLICATION_SECURITY = "Application Security"
    VULNERABILITY_MANAGEMENT = "Vulnerability Management"
    INCIDENT_RESPONSE = "Incident Response"
    BUSINESS_CONTINUITY = "Business Continuity"
    THIRD_PARTY_RISK = "Third-Party Risk"
    SECURITY_AWARENESS = "Security Awareness"


class RiskRating(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskTreatment(str, Enum):
    MITIGATE = "Mitigate"
    ACCEPT = "Accept"
    TRANSFER = "Transfer"
    AVOID = "Avoid"


class RiskStatus(str, Enum):
    OPEN = "Open"
    IN_TREATMENT = "In Treatment"
    MONITORING = "Monitoring"
    CLOSED = "Closed"


class ControlType(str, Enum):
    PREVENTIVE = "Preventive"
    DETECTIVE = "Detective"
    CORRECTIVE = "Corrective"


class TestingFrequency(str, Enum):
    CONTINUOUS = "Continuous"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUAL = "Semi-Annual"
    ANNUAL = "Annual"


class ImplementationStatus(str, Enum):
    IMPLEMENTED = "Implemented"
    PARTIALLY_IMPLEMENTED = "Partially Implemented"
    NOT_IMPLEMENTED = "Not Implemented"
    NOT_APPLICABLE = "Not Applicable"


class EvidenceType(str, Enum):
    CONFIGURATION_EXPORT = "Configuration Export"
    SCAN_REPORT = "Scan Report"
    POLICY_DOCUMENT = "Policy Document"
    PLAN_DOCUMENT = "Plan Document"
    TEST_RESULT = "Test Result"
    ACCESS_REVIEW = "Access Review"
    SCREENSHOT = "Screenshot"
    LOG_EXTRACT = "Log Extract"


class EvidenceStatus(str, Enum):
    VALID = "Valid"
    EXPIRING = "Expiring"
    EXPIRED = "Expired"


class RemediationPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RemediationStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ACCEPTED_RISK = "Accepted Risk"


class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    EXPORT = "EXPORT"
