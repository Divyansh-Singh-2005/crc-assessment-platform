"""Risk register for FinSecure Technologies (fictional).

Twenty risks spanning all nine categories and all ten assets. Likelihood and
impact are chosen so the inherent distribution spans every rating band, with
the heaviest exposure concentrated on the payment and cloud assets, which is
where a financial services firm of this size would actually carry it.

Residual scores are NOT set here. They are computed by the scoring service
from linked control assessments, so at this stage every residual equals its
inherent score. That is the correct answer for an unmitigated risk, and the
figures drop once Phase 4 links controls.

Run with:  python -m app.seed.risks
"""

from datetime import date

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.asset import Asset
from app.models.enums import RiskCategory, RiskStatus, RiskTreatment
from app.models.risk import Risk
from app.services.scoring import inherent_risk_score

RISKS = [
    dict(
        risk_ref="RISK-001",
        title="Compromise of privileged cloud accounts lacking MFA",
        description=(
            "Privileged IAM users in the production AWS account can authenticate "
            "with a password alone. Credential theft would grant an attacker "
            "administrative control over production infrastructure."
        ),
        asset_ref="ASSET-005",
        category=RiskCategory.IAM,
        threat="External attacker using credentials obtained through phishing or reuse",
        vulnerability="Multi-factor authentication not enforced on all privileged IAM users",
        likelihood=4,
        impact=5,
        risk_owner="Head of Infrastructure",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 11, 30),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-002",
        title="Cardholder data exposure through Payment API",
        description=(
            "The Payment API returns full card metadata in certain error "
            "responses, which are written to application logs retained for 90 days."
        ),
        asset_ref="ASSET-002",
        category=RiskCategory.DATA_PROTECTION,
        threat="Attacker or insider with access to application log storage",
        vulnerability="Sensitive data included in error responses and persisted to logs",
        likelihood=3,
        impact=5,
        risk_owner="Director of Payments",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 10, 31),
        status=RiskStatus.IN_TREATMENT,
    ),
    dict(
        risk_ref="RISK-003",
        title="Publicly accessible S3 bucket containing customer statements",
        description=(
            "Bucket policies are configured per team with no central guardrail. "
            "A misconfiguration would expose customer statement PDFs to the internet."
        ),
        asset_ref="ASSET-005",
        category=RiskCategory.CLOUD_SECURITY,
        threat="Opportunistic scanning of public cloud storage",
        vulnerability="No preventative service control policy blocking public bucket access",
        likelihood=3,
        impact=5,
        risk_owner="Head of Infrastructure",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 15),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-004",
        title="SQL injection in Customer Portal search functionality",
        description=(
            "Legacy search endpoints construct queries by string concatenation. "
            "Exploitation would allow extraction of customer account data."
        ),
        asset_ref="ASSET-001",
        category=RiskCategory.APPLICATION_SECURITY,
        threat="External attacker probing internet-facing application endpoints",
        vulnerability="Dynamic SQL constructed without parameterisation in legacy modules",
        likelihood=3,
        impact=5,
        risk_owner="Head of Retail Banking",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 10, 15),
        status=RiskStatus.IN_TREATMENT,
    ),
    dict(
        risk_ref="RISK-005",
        title="Unpatched critical vulnerabilities on internet-facing hosts",
        description=(
            "Patch cycles for external-facing systems average 45 days against a "
            "policy target of 14 days for critical severity findings."
        ),
        asset_ref="ASSET-001",
        category=RiskCategory.VULNERABILITY_MANAGEMENT,
        threat="Automated exploitation of a published vulnerability",
        vulnerability="Remediation timelines exceed policy for critical severity findings",
        likelihood=4,
        impact=4,
        risk_owner="Head of IT Operations",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 11, 15),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-006",
        title="Ransomware encryption of core banking data",
        description=(
            "A successful ransomware deployment reaching the core banking "
            "database would halt customer transactions and account servicing."
        ),
        asset_ref="ASSET-006",
        category=RiskCategory.BUSINESS_CONTINUITY,
        threat="Ransomware operator gaining a foothold through an employee endpoint",
        vulnerability="Backup restoration has not been tested end to end in twelve months",
        likelihood=3,
        impact=5,
        risk_owner="Head of Core Systems",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 31),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-007",
        title="Excessive standing access to the HR database",
        description=(
            "Thirty-one accounts hold read access to employee records, including "
            "eleven that have not queried the database in six months."
        ),
        asset_ref="ASSET-003",
        category=RiskCategory.IAM,
        threat="Insider misuse or compromise of an over-privileged account",
        vulnerability="No periodic access recertification for the HR data store",
        likelihood=4,
        impact=3,
        risk_owner="Chief People Officer",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 11, 30),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-008",
        title="Production data copied into the development environment",
        description=(
            "Engineering teams have historically restored production database "
            "snapshots into the lower-assurance development account for testing."
        ),
        asset_ref="ASSET-010",
        category=RiskCategory.DATA_PROTECTION,
        threat="Attacker targeting the weaker controls of a non-production environment",
        vulnerability="No enforced masking or synthetic data generation for test data",
        likelihood=4,
        impact=4,
        risk_owner="Head of Engineering",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 10, 31),
        status=RiskStatus.IN_TREATMENT,
    ),
    dict(
        risk_ref="RISK-009",
        title="Delayed detection of security incidents",
        description=(
            "Security logging is enabled but not centrally aggregated or alerted "
            "on. Mean time to detect is currently unmeasured."
        ),
        asset_ref="ASSET-005",
        category=RiskCategory.INCIDENT_RESPONSE,
        threat="Attacker operating undetected within the environment",
        vulnerability="No centralised log aggregation or alerting on security events",
        likelihood=4,
        impact=4,
        risk_owner="Head of Security Operations",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 15),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-010",
        title="Customer identity documents exposed at KYC provider",
        description=(
            "Identity documents are transmitted to an external verification "
            "provider whose security posture has not been independently assessed."
        ),
        asset_ref="ASSET-009",
        category=RiskCategory.THIRD_PARTY_RISK,
        threat="Breach of the third-party provider's environment",
        vulnerability="No security assessment or contractual security requirements in place",
        likelihood=3,
        impact=4,
        risk_owner="Head of Financial Crime",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2027, 1, 31),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-011",
        title="Successful phishing leading to credential compromise",
        description=(
            "The most recent simulated phishing exercise produced a 22 percent "
            "click rate and an 8 percent credential submission rate."
        ),
        asset_ref="ASSET-008",
        category=RiskCategory.SECURITY_AWARENESS,
        threat="Targeted phishing campaign against staff",
        vulnerability="Security awareness training is annual and not role-specific",
        likelihood=5,
        impact=3,
        risk_owner="Head of IT Operations",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 11, 30),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-012",
        title="Broken object-level authorisation in Customer Portal",
        description=(
            "Account detail endpoints authorise by session but not by resource "
            "ownership, allowing enumeration of other customers' records."
        ),
        asset_ref="ASSET-001",
        category=RiskCategory.APPLICATION_SECURITY,
        threat="Authenticated customer manipulating identifiers in API requests",
        vulnerability="Authorisation checks omitted at the object level",
        likelihood=3,
        impact=4,
        risk_owner="Head of Retail Banking",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 10, 31),
        status=RiskStatus.IN_TREATMENT,
    ),
    dict(
        risk_ref="RISK-013",
        title="Unencrypted database backups in secondary storage",
        description=(
            "Nightly database exports are written to secondary storage without "
            "encryption at rest and retained for 35 days."
        ),
        asset_ref="ASSET-006",
        category=RiskCategory.DATA_PROTECTION,
        threat="Unauthorised access to backup storage",
        vulnerability="Encryption at rest not applied to backup exports",
        likelihood=2,
        impact=5,
        risk_owner="Head of Core Systems",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 31),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-014",
        title="Lateral movement from a compromised endpoint",
        description=(
            "The corporate network is flat between office segments, allowing an "
            "attacker on one endpoint broad reach across internal systems."
        ),
        asset_ref="ASSET-007",
        category=RiskCategory.CLOUD_SECURITY,
        threat="Attacker who has established a foothold on an employee device",
        vulnerability="Insufficient network segmentation between user and server segments",
        likelihood=3,
        impact=4,
        risk_owner="Head of Infrastructure",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2027, 2, 28),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-015",
        title="Incident response plan untested against a live scenario",
        description=(
            "A documented incident response plan exists but has never been "
            "exercised, and on-call escalation paths are unverified."
        ),
        asset_ref="ASSET-005",
        category=RiskCategory.INCIDENT_RESPONSE,
        threat="Any security incident requiring coordinated response",
        vulnerability="No tabletop exercise or simulation conducted since the plan was written",
        likelihood=3,
        impact=3,
        risk_owner="Head of Security Operations",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 15),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-016",
        title="Analytics platform retains identifiable customer data",
        description=(
            "Pseudonymisation is applied on ingestion but several derived tables "
            "retain fields sufficient to re-identify individual customers."
        ),
        asset_ref="ASSET-004",
        category=RiskCategory.DATA_PROTECTION,
        threat="Internal user accessing data beyond their legitimate purpose",
        vulnerability="Re-identification possible from retained derived attributes",
        likelihood=3,
        impact=3,
        risk_owner="Head of Data & Analytics",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2027, 1, 31),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-017",
        title="Dormant accounts retained after employee departure",
        description=(
            "Leaver processing is manual and dependent on HR notification. Nine "
            "accounts remained enabled beyond thirty days after departure."
        ),
        asset_ref="ASSET-003",
        category=RiskCategory.IAM,
        threat="Former employee or attacker using an orphaned account",
        vulnerability="No automated deprovisioning triggered by HR leaver events",
        likelihood=3,
        impact=3,
        risk_owner="Chief People Officer",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 11, 30),
        status=RiskStatus.MONITORING,
    ),
    dict(
        risk_ref="RISK-018",
        title="Third-party library vulnerabilities in the analytics stack",
        description=(
            "Dependency scanning is not integrated into the analytics build "
            "pipeline, so vulnerable packages reach the environment undetected."
        ),
        asset_ref="ASSET-004",
        category=RiskCategory.VULNERABILITY_MANAGEMENT,
        threat="Exploitation of a known vulnerability in an open-source dependency",
        vulnerability="No software composition analysis in the analytics pipeline",
        likelihood=3,
        impact=3,
        risk_owner="Head of Data & Analytics",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2026, 12, 31),
        status=RiskStatus.OPEN,
    ),
    dict(
        risk_ref="RISK-019",
        title="Extended recovery time for the analytics platform",
        description=(
            "The analytics platform has no documented recovery time objective "
            "and no tested restoration procedure."
        ),
        asset_ref="ASSET-004",
        category=RiskCategory.BUSINESS_CONTINUITY,
        threat="Infrastructure failure or destructive incident",
        vulnerability="No defined RTO or tested recovery procedure for this platform",
        likelihood=2,
        impact=3,
        risk_owner="Head of Data & Analytics",
        treatment=RiskTreatment.ACCEPT,
        due_date=None,
        status=RiskStatus.MONITORING,
    ),
    dict(
        risk_ref="RISK-020",
        title="Unapproved software installed on employee devices",
        description=(
            "Local administrator rights are granted to approximately sixty "
            "technical staff, permitting installation of unreviewed software."
        ),
        asset_ref="ASSET-008",
        category=RiskCategory.SECURITY_AWARENESS,
        threat="Introduction of malicious or vulnerable software by a user",
        vulnerability="Local administrator rights granted broadly to technical staff",
        likelihood=3,
        impact=2,
        risk_owner="Head of IT Operations",
        treatment=RiskTreatment.MITIGATE,
        due_date=date(2027, 3, 31),
        status=RiskStatus.OPEN,
    ),
]


def seed_risks() -> None:
    with SessionLocal() as db:
        assets = {asset.asset_ref: asset.id for asset in db.scalars(select(Asset))}
        if not assets:
            print("  No assets found. Run 'python -m app.seed.assets' first.")
            return

        for record in RISKS:
            data = dict(record)
            asset_ref = data.pop("asset_ref")
            if db.scalar(select(Risk).where(Risk.risk_ref == data["risk_ref"])):
                print(f"  exists   {data['risk_ref']}")
                continue
            if asset_ref not in assets:
                print(f"  skipped  {data['risk_ref']}  (asset {asset_ref} missing)")
                continue

            inherent = inherent_risk_score(data["likelihood"], data["impact"])
            db.add(
                Risk(
                    **data,
                    asset_id=assets[asset_ref],
                    inherent_score=inherent,
                    # Residual equals inherent until controls are linked and
                    # assessed. An unmitigated risk carries full exposure.
                    residual_score=inherent,
                )
            )
            print(
                f"  created  {data['risk_ref']}  L{data['likelihood']} x I{data['impact']}"
                f" = {inherent:2d}  {data['title'][:52]}"
            )
        db.commit()


if __name__ == "__main__":
    print("Seeding FinSecure Technologies risk register")
    seed_risks()
    print("Done.")