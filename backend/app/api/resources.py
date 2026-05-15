from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import is_admin_user
from app.api.compliance import get_own_agent_profile_or_404
from app.api.deps import get_current_active_user
from app.core.resources import SUPPLIER_ACCESS_AGENT_STATUSES
from app.db.session import get_db
from app.models.resources import SupplierAccess
from app.models.training import TrainingModule
from app.models.user import User
from app.schemas.resources import (
    SupplierAccessCreate,
    SupplierAccessRead,
    SupplierAccessUpdate,
)


router = APIRouter(tags=["Supplier Access"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage supplier access.",
        )


def get_training_module_or_404(db: Session, training_module_id: int | None) -> None:
    if training_module_id is None:
        return
    training_module = db.get(TrainingModule, training_module_id)
    if training_module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related training module not found.",
        )


def get_supplier_access_or_404(db: Session, supplier_access_id: int) -> SupplierAccess:
    supplier_access = db.get(SupplierAccess, supplier_access_id)
    if supplier_access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier access record not found.",
        )
    return supplier_access


def require_supplier_access_for_agent(db: Session, current_user: User) -> None:
    agent_profile = get_own_agent_profile_or_404(db, current_user)
    if agent_profile.status not in SUPPLIER_ACCESS_AGENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier Access is locked until the agent is Approved to Trade.",
        )


@router.get("/supplier-access", response_model=list[SupplierAccessRead])
def list_supplier_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[SupplierAccess]:
    query = select(SupplierAccess).order_by(SupplierAccess.supplier_name, SupplierAccess.id)
    if not is_admin_user(current_user):
        require_supplier_access_for_agent(db, current_user)
        query = query.where(SupplierAccess.visible_to_agents.is_(True))
    return list(db.scalars(query))


@router.post("/supplier-access", response_model=SupplierAccessRead, status_code=status.HTTP_201_CREATED)
def create_supplier_access(
    request: SupplierAccessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SupplierAccess:
    require_admin_user(current_user)
    get_training_module_or_404(db, request.related_training_module)

    supplier_access = SupplierAccess(
        supplier_name=request.supplier_name,
        supplier_type=request.supplier_type,
        portal_url=request.portal_url,
        login_instructions=request.login_instructions,
        access_notes=request.access_notes,
        training_required=request.training_required,
        related_training_module=request.related_training_module,
        visible_to_agents=request.visible_to_agents,
        created_by=current_user.id,
    )
    db.add(supplier_access)
    db.commit()
    db.refresh(supplier_access)
    return supplier_access


@router.put("/supplier-access/{supplier_access_id}", response_model=SupplierAccessRead)
def update_supplier_access(
    supplier_access_id: int,
    request: SupplierAccessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SupplierAccess:
    require_admin_user(current_user)
    supplier_access = get_supplier_access_or_404(db, supplier_access_id)
    get_training_module_or_404(db, request.related_training_module)

    supplier_access.supplier_name = request.supplier_name
    supplier_access.supplier_type = request.supplier_type
    supplier_access.portal_url = request.portal_url
    supplier_access.login_instructions = request.login_instructions
    supplier_access.access_notes = request.access_notes
    supplier_access.training_required = request.training_required
    supplier_access.related_training_module = request.related_training_module
    supplier_access.visible_to_agents = request.visible_to_agents

    db.commit()
    db.refresh(supplier_access)
    return supplier_access
