"""Risk register business rules.

The central responsibility here is that scores are always derived, never
supplied. Every path that can change a risk's exposure ends in a call to
recalculate(), so the stored residual can never drift from the evidence.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import ControlAssessment
from app.models.control import Control
from app.models.enums import AuditAction, ImplementationStatus
from app.models.risk import Risk, RiskControl
from app.models.user import User
from app.repositories import asset as asset_repo
from app.repositories import risk as repo
from app.schemas.risk import RiskCreate, RiskUpdate
from app.services import audit
from app.services.scoring import (
    ControlContribution,
    aggregate_effectiveness,
    inherent_risk_score,
    rating_for_score,
    residual_risk_score,
)


class RiskError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def latest_assessment(db: Session, control_id: int) -> ControlAssessment | None:
    """The most recent assessment of a control.

    Assessments are append-only, so a control accumulates history. Only the
    latest one carries effectiveness credit: a control that passed testing in
    January and failed in June is a failed control today.
    """
    return db.scalar(
        select(ControlAssessment)
        .where(ControlAssessment.control_id == control_id)
        .order_by(ControlAssessment.assessment_date.desc(), ControlAssessment.id.desc())
        .limit(1)
    )


def contributions_for(db: Session, risk: Risk) -> list[ControlContribution]:
    """Build the scoring inputs from this risk's linked controls.

    A linked control with no assessment yet contributes nothing. An unassessed
    control is an unproven control, and unproven controls earn no credit.
    """
    contributions: list[ControlContribution] = []
    for link in risk.control_links:
        assessment = latest_assessment(db, link.control_id)
        if assessment is None:
            continue
        if assessment.implementation_status == ImplementationStatus.NOT_APPLICABLE:
            continue
        contributions.append(
            ControlContribution(
                effectiveness=Decimal(assessment.effectiveness),
                weight=Decimal(link.weight),
            )
        )
    return contributions


def recalculate(db: Session, risk: Risk) -> Risk:
    """Recompute both scores from current inputs and stamp the time.

    residual_calculated_at matters: a residual score is only valid as of the
    assessments that produced it. Being able to say when it was computed is
    the difference between a risk register and a spreadsheet of opinions.
    """
    risk.inherent_score = inherent_risk_score(risk.likelihood, risk.impact)
    aggregate = aggregate_effectiveness(contributions_for(db, risk))
    risk.residual_score = residual_risk_score(risk.inherent_score, aggregate)
    risk.residual_calculated_at = datetime.now(timezone.utc)
    return risk


def create_risk(
    db: Session,
    payload: RiskCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> Risk:
    if repo.get_by_ref(db, payload.risk_ref) is not None:
        raise RiskError(f"Risk reference {payload.risk_ref} already exists", 409)
    if asset_repo.get_by_id(db, payload.asset_id) is None:
        raise RiskError(f"Asset {payload.asset_id} does not exist", 422)

    risk = Risk(**payload.model_dump(), inherent_score=0, residual_score=0)
    recalculate(db, risk)
    db.add(risk)
    db.flush()

    audit.record(
        db,
        action=AuditAction.CREATE,
        entity_type="Risk",
        entity_id=risk.risk_ref,
        description=(
            f"Created risk {risk.risk_ref} ({risk.title}); "
            f"L{risk.likelihood} x I{risk.impact} = inherent {risk.inherent_score} "
            f"({rating_for_score(risk.inherent_score).value})"
        ),
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    return repo.get_by_id(db, risk.id)


def update_risk(
    db: Session,
    risk_id: int,
    payload: RiskUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> Risk:
    risk = repo.get_by_id(db, risk_id)
    if risk is None:
        raise RiskError("Risk not found", 404)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise RiskError("No fields supplied to update", 422)

    if "asset_id" in changes and asset_repo.get_by_id(db, changes["asset_id"]) is None:
        raise RiskError(f"Asset {changes['asset_id']} does not exist", 422)

    previous_residual = risk.residual_score
    changed_fields = []
    for field, new_value in changes.items():
        old_value = getattr(risk, field)
        if old_value == new_value:
            continue
        old_display = old_value.value if hasattr(old_value, "value") else old_value
        new_display = new_value.value if hasattr(new_value, "value") else new_value
        changed_fields.append(f"{field}: {old_display} -> {new_display}")
        setattr(risk, field, new_value)

    if not changed_fields:
        return risk

    recalculate(db, risk)
    if risk.residual_score != previous_residual:
        changed_fields.append(
            f"residual_score: {previous_residual} -> {risk.residual_score}"
        )

    audit.record(
        db,
        action=AuditAction.UPDATE,
        entity_type="Risk",
        entity_id=risk.risk_ref,
        description=f"Updated risk {risk.risk_ref}; " + "; ".join(changed_fields),
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    return repo.get_by_id(db, risk_id)


def delete_risk(
    db: Session,
    risk_id: int,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    risk = repo.get_by_id(db, risk_id)
    if risk is None:
        raise RiskError("Risk not found", 404)

    reference, title = risk.risk_ref, risk.title
    db.delete(risk)
    audit.record(
        db,
        action=AuditAction.DELETE,
        entity_type="Risk",
        entity_id=reference,
        description=f"Deleted risk {reference} ({title})",
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()


def link_control(
    db: Session,
    risk_id: int,
    control_id: int,
    weight: Decimal,
    *,
    actor: User,
    request: Request | None = None,
) -> Risk:
    """Credit a control against a risk and recompute the residual."""
    risk = repo.get_by_id(db, risk_id)
    if risk is None:
        raise RiskError("Risk not found", 404)
    control = db.get(Control, control_id)
    if control is None:
        raise RiskError(f"Control {control_id} does not exist", 422)
    if repo.get_link(db, risk_id, control_id) is not None:
        raise RiskError(f"{control.control_ref} is already linked to this risk", 409)

    db.add(RiskControl(risk_id=risk_id, control_id=control_id, weight=weight))
    db.flush()
    db.refresh(risk)

    before = risk.residual_score
    recalculate(db, risk)

    audit.record(
        db,
        action=AuditAction.UPDATE,
        entity_type="Risk",
        entity_id=risk.risk_ref,
        description=(
            f"Linked control {control.control_ref} (weight {weight}) to {risk.risk_ref}; "
            f"residual {before} -> {risk.residual_score}"
        ),
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    return repo.get_by_id(db, risk_id)


def unlink_control(
    db: Session,
    risk_id: int,
    control_id: int,
    *,
    actor: User,
    request: Request | None = None,
) -> Risk:
    risk = repo.get_by_id(db, risk_id)
    if risk is None:
        raise RiskError("Risk not found", 404)
    link = repo.get_link(db, risk_id, control_id)
    if link is None:
        raise RiskError("That control is not linked to this risk", 404)

    control_ref = link.control.control_ref
    db.delete(link)
    db.flush()
    db.refresh(risk)

    before = risk.residual_score
    recalculate(db, risk)

    audit.record(
        db,
        action=AuditAction.UPDATE,
        entity_type="Risk",
        entity_id=risk.risk_ref,
        description=(
            f"Unlinked control {control_ref} from {risk.risk_ref}; "
            f"residual {before} -> {risk.residual_score}"
        ),
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    return repo.get_by_id(db, risk_id)


def recalculate_all(db: Session) -> int:
    """Recompute every risk. Called after control assessments change, since
    a new assessment can move the residual score of many risks at once."""
    risks = list(db.scalars(select(Risk)))
    for risk in risks:
        db.refresh(risk)
        recalculate(db, risk)
    db.commit()
    return len(risks)