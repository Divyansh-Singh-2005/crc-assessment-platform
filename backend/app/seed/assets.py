"""Asset inventory for FinSecure Technologies (fictional).

Ten assets spanning applications, data stores, cloud infrastructure and a
third-party service, with a spread of criticality and data classification so
that downstream risk scoring produces a realistic distribution rather than a
uniform one.

Run with:  python -m app.seed.assets
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.asset import Asset
from app.models.enums import AssetType, DataClassification, Environment

ASSETS = [
    dict(
        asset_ref="ASSET-001",
        name="Customer Portal",
        asset_type=AssetType.APPLICATION,
        business_owner="Head of Retail Banking",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.CONFIDENTIAL,
        criticality=5,
        description=(
            "Internet-facing web application used by approximately 40,000 retail "
            "customers for account access, statements and payment initiation."
        ),
    ),
    dict(
        asset_ref="ASSET-002",
        name="Payment API",
        asset_type=AssetType.APPLICATION,
        business_owner="Director of Payments",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.RESTRICTED,
        criticality=5,
        description=(
            "REST API processing card and account-to-account payments, integrated "
            "with two external payment networks. Handles cardholder data."
        ),
    ),
    dict(
        asset_ref="ASSET-003",
        name="HR Database",
        asset_type=AssetType.DATABASE,
        business_owner="Chief People Officer",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.CONFIDENTIAL,
        criticality=4,
        description=(
            "PostgreSQL database holding employee records, payroll references and "
            "performance data for approximately 500 staff."
        ),
    ),
    dict(
        asset_ref="ASSET-004",
        name="Data Analytics Platform",
        asset_type=AssetType.APPLICATION,
        business_owner="Head of Data & Analytics",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.CONFIDENTIAL,
        criticality=4,
        description=(
            "Analytics environment aggregating customer transaction data for "
            "reporting and model development. Contains pseudonymised extracts."
        ),
    ),
    dict(
        asset_ref="ASSET-005",
        name="AWS Production Environment",
        asset_type=AssetType.CLOUD_ENVIRONMENT,
        business_owner="Head of Infrastructure",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.RESTRICTED,
        criticality=5,
        description=(
            "Primary AWS account hosting production workloads across two regions. "
            "Includes EC2, RDS, S3 and IAM configuration for all production systems."
        ),
    ),
    dict(
        asset_ref="ASSET-006",
        name="Core Banking Database",
        asset_type=AssetType.DATABASE,
        business_owner="Head of Core Systems",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.RESTRICTED,
        criticality=5,
        description=(
            "System of record for customer accounts and balances. Any loss of "
            "integrity here is a direct financial and regulatory exposure."
        ),
    ),
    dict(
        asset_ref="ASSET-007",
        name="Corporate Network",
        asset_type=AssetType.NETWORK,
        business_owner="Head of Infrastructure",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.INTERNAL,
        criticality=4,
        description=(
            "Head office and branch network including VPN concentrators for remote "
            "staff and site-to-site links to the data centre."
        ),
    ),
    dict(
        asset_ref="ASSET-008",
        name="Employee Endpoints",
        asset_type=AssetType.ENDPOINT,
        business_owner="Head of IT Operations",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.INTERNAL,
        criticality=3,
        description=(
            "Approximately 520 managed laptops and mobile devices. Primary entry "
            "point for phishing and malware."
        ),
    ),
    dict(
        asset_ref="ASSET-009",
        name="KYC Verification Service",
        asset_type=AssetType.THIRD_PARTY_SERVICE,
        business_owner="Head of Financial Crime",
        environment=Environment.PRODUCTION,
        data_classification=DataClassification.CONFIDENTIAL,
        criticality=4,
        description=(
            "External identity verification provider receiving customer identity "
            "documents during onboarding. Data leaves the organisation's boundary."
        ),
    ),
    dict(
        asset_ref="ASSET-010",
        name="Development & Test Environment",
        asset_type=AssetType.CLOUD_ENVIRONMENT,
        environment=Environment.DEVELOPMENT,
        business_owner="Head of Engineering",
        data_classification=DataClassification.INTERNAL,
        criticality=2,
        description=(
            "Separate AWS account for build and test. Historically has received "
            "copies of production data for testing purposes."
        ),
    ),
]


def seed_assets() -> None:
    with SessionLocal() as db:
        for record in ASSETS:
            if db.scalar(select(Asset).where(Asset.asset_ref == record["asset_ref"])):
                print(f"  exists   {record['asset_ref']}  {record['name']}")
                continue
            db.add(Asset(**record))
            print(f"  created  {record['asset_ref']}  {record['name']}")
        db.commit()


if __name__ == "__main__":
    print("Seeding FinSecure Technologies asset inventory")
    seed_assets()
    print("Done.")