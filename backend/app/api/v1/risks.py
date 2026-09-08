"""Risk register endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_analyst, require_viewer
from app.models.enums import RiskCategory, RiskStatus, RiskTreatment
from app.models.risk import Risk
from app.models.user import User
from app.repositories import risk as repo
from app.schemas.common import Page
from app.schemas.risk import (
    ControlLinkRequest,
    LinkedControl,
    RiskCreate,
    RiskDetail,
    RiskRead,
    RiskUpdate,
)
from app.services import risk as service
from app.services.risk import RiskError, latest_assessment
from app.services.scoring import aggregate_effectiveness, rating_for_score

router = APIRouter(prefix="/risks", tags=["risks"])


def _to_read(risk: Risk) -> RiskRead:
    """Attach the derived ratings.

    Ratings are computed at serialisation time rather than stored, so they can
    never contradict the score they describe.
    """
    return RiskRead(
        **{
            key: getattr(risk, key)
            for key in (
                "id", "risk_ref", "title", "description", "category", "threat",
                "vulnerability", "likelihood", "impact", "inherent_score",
                "residual_score", "residual_calculated_at", "risk_owner",
                "treatment", "due_date", "status", "created_at", "updated_at",
            )
        },
        inherent_rating=rating_for_score(risk.inherent_score),
        residual_rating=rating_for_score(risk.residual_score),
        risk_reduction=risk.inherent_score - risk.residual_score,
        asset=risk.asset,
    )


@router.get("", response_model=Page[RiskRead])
def list_risks(
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None, max_length=100),
    category: RiskCategory | None = None,
    status_filter: RiskStatus | None = Query(default=None, alias="status"),
    treatment: RiskTreatment | None = None,
    asset_id: int | None = Query(default=None, gt=0),
    residual_rating: str | None = Query(default=None, pattern="^(Low|Medium|High|Critical)$"),
    min_residual: int | None = Query(default=None, ge=1, le=25),
    sort_by: str = Query(default="residual_score"),
    descending: bool = True,
) -> Page[RiskRead]:
    """Paged risk register, sorted by residual risk descending by default."""
    items, total = repo.list_risks(
        db,
        offset=(page - 1) * page_size,
        limit=page_size,
        sort_by=sort_by,
        descending=descending,
        search=search,
        category=category,
        status=status_filter,
        treatment=treatment,
        asset_id=asset_id,
        residual_rating=residual_rating,
        min_residual=min_residual,
    )
    return Page[RiskRead](
        items=[_to_read(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/top", response_model=list[RiskRead])
def top_risks(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
) -> list[RiskRead]:
    """Highest residual risks: the remediation priority list."""
    return [_to_read(item) for item in repo.top_by_residual(db, limit)]


@router.get("/next-reference", response_model=dict)
def next_reference(
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
) -> dict[str, str]:
    return {"risk_ref": repo.next_reference(db)}


@router.get("/{risk_id}", response_model=RiskDetail)
def get_risk(
    risk_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
) -> RiskDetail:
    """Full detail including the calculation chain behind the residual score."""
    risk = repo.get_by_id(db, risk_id)
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")

    linked = []
    for link in risk.control_links:
        assessment = latest_assessment(db, link.control_id)
        effectiveness = Decimal(assessment.effectiveness) if assessment else Decimal("0.00")
        linked.append(
            LinkedControl(
                control_id=link.control_id,
                control_ref=link.control.control_ref,
                name=link.control.name,
                weight=Decimal(link.weight),
                effectiveness=effectiveness,
                implementation_status=(
                    assessment.implementation_status.value if assessment else None
                ),
                assessed_on=assessment.assessment_date if assessment else None,
                contribution=effectiveness * Decimal(link.weight),
            )
        )

    return RiskDetail(
        **_to_read(risk).model_dump(),
        aggregate_effectiveness=aggregate_effectiveness(service.contributions_for(db, risk)),
        linked_controls=linked,
    )


@router.post("", response_model=RiskRead, status_code=status.HTTP_201_CREATED)
def create_risk(
    payload: RiskCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> RiskRead:
    try:
        risk = service.create_risk(db, payload, actor=actor, request=request)
    except RiskError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _to_read(risk)


@router.put("/{risk_id}", response_model=RiskRead)
def update_risk(
    risk_id: int,
    payload: RiskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> RiskRead:
    try:
        risk = service.update_risk(db, risk_id, payload, actor=actor, request=request)
    except RiskError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _to_read(risk)


@router.delete("/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk(
    risk_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> None:
    try:
        service.delete_risk(db, risk_id, actor=actor, request=request)
    except RiskError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@router.post("/{risk_id}/controls", response_model=RiskRead)
def link_control(
    risk_id: int,
    payload: ControlLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> RiskRead:
    """Credit a control against this risk. Recomputes the residual score."""
    try:
        risk = service.link_control(
            db, risk_id, payload.control_id, payload.weight, actor=actor, request=request
        )
    except RiskError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _to_read(risk)


@router.delete("/{risk_id}/controls/{control_id}", response_model=RiskRead)
def unlink_control(
    risk_id: int,
    control_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_analyst),
) -> RiskRead:
    try:
        risk = service.unlink_control(db, risk_id, control_id, actor=actor, request=request)
    except RiskError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _to_read(risk)