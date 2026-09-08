"""Database access for the risk register."""

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.enums import RiskCategory, RiskStatus, RiskTreatment
from app.models.risk import Risk, RiskControl

# Score ranges backing each severity band. Filtering by rating is translated
# into a score range here so the bands are defined once, in scoring.py, and
# never duplicated as literals across the query layer.
RATING_RANGES = {
    "Low": (1, 4),
    "Medium": (5, 9),
    "High": (10, 16),
    "Critical": (17, 25),
}


def _base_query(
    *,
    search: str | None = None,
    category: RiskCategory | None = None,
    status: RiskStatus | None = None,
    treatment: RiskTreatment | None = None,
    asset_id: int | None = None,
    residual_rating: str | None = None,
    min_residual: int | None = None,
) -> Select:
    query = select(Risk).options(joinedload(Risk.asset))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Risk.title.ilike(pattern),
                Risk.risk_ref.ilike(pattern),
                Risk.description.ilike(pattern),
                Risk.risk_owner.ilike(pattern),
            )
        )
    if category is not None:
        query = query.where(Risk.category == category)
    if status is not None:
        query = query.where(Risk.status == status)
    if treatment is not None:
        query = query.where(Risk.treatment == treatment)
    if asset_id is not None:
        query = query.where(Risk.asset_id == asset_id)
    if residual_rating in RATING_RANGES:
        low, high = RATING_RANGES[residual_rating]
        query = query.where(Risk.residual_score.between(low, high))
    if min_residual is not None:
        query = query.where(Risk.residual_score >= min_residual)

    return query


def list_risks(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 25,
    sort_by: str = "residual_score",
    descending: bool = True,
    **filters,
) -> tuple[list[Risk], int]:
    query = _base_query(**filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    sortable = {
        "risk_ref": Risk.risk_ref,
        "title": Risk.title,
        "inherent_score": Risk.inherent_score,
        "residual_score": Risk.residual_score,
        "likelihood": Risk.likelihood,
        "impact": Risk.impact,
        "due_date": Risk.due_date,
        "created_at": Risk.created_at,
    }
    column = sortable.get(sort_by, Risk.residual_score)

    # Secondary sort on risk_ref keeps paging stable: without a tiebreaker,
    # rows with equal residual scores can reappear or vanish across pages.
    query = query.order_by(column.desc() if descending else column.asc(), Risk.risk_ref)

    items = list(db.scalars(query.offset(offset).limit(limit)).unique())
    return items, total


def get_by_id(db: Session, risk_id: int) -> Risk | None:
    return db.scalar(
        select(Risk)
        .where(Risk.id == risk_id)
        .options(
            joinedload(Risk.asset),
            selectinload(Risk.control_links).joinedload(RiskControl.control),
        )
    )


def get_by_ref(db: Session, risk_ref: str) -> Risk | None:
    return db.scalar(select(Risk).where(Risk.risk_ref == risk_ref))


def get_link(db: Session, risk_id: int, control_id: int) -> RiskControl | None:
    return db.get(RiskControl, {"risk_id": risk_id, "control_id": control_id})


def top_by_residual(db: Session, limit: int = 10) -> list[Risk]:
    """Highest residual risks: what remains after control credit, which is
    what a remediation programme should be prioritised against."""
    return list(
        db.scalars(
            select(Risk)
            .options(joinedload(Risk.asset))
            .order_by(Risk.residual_score.desc(), Risk.risk_ref)
            .limit(limit)
        ).unique()
    )


def next_reference(db: Session) -> str:
    highest = db.scalar(select(func.max(Risk.risk_ref)))
    if not highest:
        return "RISK-001"
    try:
        return f"RISK-{int(highest.split('-')[1]) + 1:03d}"
    except (IndexError, ValueError):
        return "RISK-001"