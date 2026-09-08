"""Database access for assets.

The repository owns query construction and nothing else. Keeping SQLAlchemy
here means the router never builds a query and the service never imports the
session API, which is what makes the business logic testable in isolation.
"""

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AssetType, DataClassification, Environment


def _base_query(
    *,
    search: str | None = None,
    asset_type: AssetType | None = None,
    environment: Environment | None = None,
    data_classification: DataClassification | None = None,
    criticality: int | None = None,
) -> Select:
    query = select(Asset)

    if search:
        # ILIKE with a bound parameter. The wildcards are added to the value,
        # not concatenated into the SQL text, so the pattern cannot alter the
        # statement. This is parameterisation, not escaping.
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Asset.name.ilike(pattern),
                Asset.asset_ref.ilike(pattern),
                Asset.business_owner.ilike(pattern),
            )
        )
    if asset_type is not None:
        query = query.where(Asset.asset_type == asset_type)
    if environment is not None:
        query = query.where(Asset.environment == environment)
    if data_classification is not None:
        query = query.where(Asset.data_classification == data_classification)
    if criticality is not None:
        query = query.where(Asset.criticality == criticality)

    return query


def list_assets(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 25,
    sort_by: str = "asset_ref",
    descending: bool = False,
    **filters,
) -> tuple[list[Asset], int]:
    """Return one page of assets and the total matching count."""
    query = _base_query(**filters)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Sort keys are resolved against an allowlist of real columns rather than
    # interpolated. An arbitrary string reaching ORDER BY would be an
    # injection point even through the ORM.
    sortable = {
        "asset_ref": Asset.asset_ref,
        "name": Asset.name,
        "asset_type": Asset.asset_type,
        "criticality": Asset.criticality,
        "environment": Asset.environment,
        "created_at": Asset.created_at,
    }
    column = sortable.get(sort_by, Asset.asset_ref)
    query = query.order_by(column.desc() if descending else column.asc())

    items = list(db.scalars(query.offset(offset).limit(limit)))
    return items, total


def get_by_id(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def get_by_ref(db: Session, asset_ref: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.asset_ref == asset_ref))


def count_linked_risks(db: Session, asset_id: int) -> int:
    from app.models.risk import Risk

    return db.scalar(select(func.count()).select_from(Risk).where(Risk.asset_id == asset_id)) or 0


def next_reference(db: Session) -> str:
    """Suggest the next free ASSET-nnn reference."""
    highest = db.scalar(select(func.max(Asset.asset_ref)))
    if not highest:
        return "ASSET-001"
    try:
        return f"ASSET-{int(highest.split('-')[1]) + 1:03d}"
    except (IndexError, ValueError):
        return "ASSET-001"