"""Asset business rules."""

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AuditAction
from app.models.user import User
from app.repositories import asset as repo
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services import audit


class AssetError(Exception):
    """Domain error carrying an HTTP status for the router to translate."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def create_asset(
    db: Session,
    payload: AssetCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> Asset:
    if repo.get_by_ref(db, payload.asset_ref) is not None:
        raise AssetError(f"Asset reference {payload.asset_ref} already exists", 409)

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.flush()

    audit.record(
        db,
        action=AuditAction.CREATE,
        entity_type="Asset",
        entity_id=asset.asset_ref,
        description=f"Created asset {asset.asset_ref} ({asset.name})",
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session,
    asset_id: int,
    payload: AssetUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> Asset:
    asset = repo.get_by_id(db, asset_id)
    if asset is None:
        raise AssetError("Asset not found", 404)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise AssetError("No fields supplied to update", 422)

    # The audit description names each field and both values. "Asset updated"
    # would satisfy the schema and tell an investigator nothing.
    changed_fields = []
    for field, new_value in changes.items():
        old_value = getattr(asset, field)
        if old_value == new_value:
            continue
        old_display = old_value.value if hasattr(old_value, "value") else old_value
        new_display = new_value.value if hasattr(new_value, "value") else new_value
        changed_fields.append(f"{field}: {old_display} -> {new_display}")
        setattr(asset, field, new_value)

    if not changed_fields:
        return asset

    audit.record(
        db,
        action=AuditAction.UPDATE,
        entity_type="Asset",
        entity_id=asset.asset_ref,
        description=f"Updated asset {asset.asset_ref}; " + "; ".join(changed_fields),
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(
    db: Session,
    asset_id: int,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    asset = repo.get_by_id(db, asset_id)
    if asset is None:
        raise AssetError("Asset not found", 404)

    # Refuse rather than cascade. Deleting an asset that risks point at would
    # silently destroy risk records, and the database enforces this too via
    # ON DELETE RESTRICT. Checking here lets the API explain why.
    linked = repo.count_linked_risks(db, asset_id)
    if linked:
        raise AssetError(
            f"Cannot delete {asset.asset_ref}: {linked} risk(s) reference this asset. "
            "Reassign or remove those risks first.",
            409,
        )

    reference, name = asset.asset_ref, asset.name
    db.delete(asset)

    audit.record(
        db,
        action=AuditAction.DELETE,
        entity_type="Asset",
        entity_id=reference,
        description=f"Deleted asset {reference} ({name})",
        user=actor,
        request=request,
        commit=False,
    )
    db.commit()