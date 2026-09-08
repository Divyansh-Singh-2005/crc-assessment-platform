"""Asset inventory endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_analyst, require_viewer
from app.models.enums import AssetType, DataClassification, Environment
from app.models.user import User
from app.repositories import asset as repo
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.common import Page
from app.services import asset as service
from app.services.asset import AssetError

router = APIRouter(prefix="/assets", tags=["assets"])


def _handle(error: AssetError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


@router.get("", response_model=Page[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None, max_length=100),
    asset_type: AssetType | None = None,
    environment: Environment | None = None,
    data_classification: DataClassification | None = None,
    criticality: int | None = Query(default=None, ge=1, le=5),
    sort_by: str = Query(default="asset_ref"),
    descending: bool = False,
) -> Page[AssetRead]:
    """Paged, filterable asset inventory. Readable by any authenticated role."""
    items, total = repo.list_assets(
        db,
        offset=(page - 1) * page_size,
        limit=page_size,
        sort_by=sort_by,
        descending=descending,
        search=search,
        asset_type=asset_type,
        environment=environment,
        data_classification=data_classification,
        criticality=criticality,
    )
    return Page[AssetRead](
        items=[AssetRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/next-reference", response_model=dict)
def next_reference(
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
) -> dict[str, str]:
    """Suggest the next unused asset reference for the create form."""
    return {"asset_ref": repo.next_reference(db)}


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
) -> AssetRead:
    asset = repo.get_by_id(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return AssetRead.model_validate(asset)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> AssetRead:
    """Create an asset. Analyst or administrator only."""
    try:
        asset = service.create_asset(db, payload, actor=actor, request=request)
    except AssetError as error:
        raise _handle(error) from None
    return AssetRead.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> AssetRead:
    try:
        asset = service.update_asset(db, asset_id, payload, actor=actor, request=request)
    except AssetError as error:
        raise _handle(error) from None
    return AssetRead.model_validate(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> None:
    try:
        service.delete_asset(db, asset_id, actor=actor, request=request)
    except AssetError as error:
        raise _handle(error) from None