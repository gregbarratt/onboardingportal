from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import is_admin_user
from app.api.compliance import get_own_agent_profile_or_404
from app.api.deps import get_current_active_user
from app.core.resources import SOCIAL_MEDIA_POLICY_TYPE, SUPPLIER_ACCESS_AGENT_STATUSES
from app.db.session import get_db
from app.models.compliance import CompliancePolicy, PolicyAcceptance
from app.models.resources import MarketingAsset, SupplierAccess
from app.models.training import TrainingModule
from app.models.user import User
from app.schemas.resources import (
    MarketingAssetCreate,
    MarketingAssetRead,
    SupplierAccessCreate,
    SupplierAccessRead,
)


router = APIRouter(tags=["Supplier Access and Marketing Hub"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage supplier access and marketing assets.",
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


def require_supplier_access_for_agent(db: Session, current_user: User) -> None:
    agent_profile = get_own_agent_profile_or_404(db, current_user)
    if agent_profile.status not in SUPPLIER_ACCESS_AGENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier Access is locked until the agent is Approved to Trade.",
        )


def has_accepted_social_media_policy(db: Session, agent_id: int) -> bool:
    policies = list(
        db.scalars(
            select(CompliancePolicy).where(
                CompliancePolicy.policy_type == SOCIAL_MEDIA_POLICY_TYPE,
                CompliancePolicy.published_status == "Published",
                CompliancePolicy.requires_acceptance.is_(True),
            )
        )
    )
    if not policies:
        return False

    policy_ids = [policy.id for policy in policies]
    acceptances = list(
        db.scalars(
            select(PolicyAcceptance).where(
                PolicyAcceptance.agent_id == agent_id,
                PolicyAcceptance.policy_id.in_(policy_ids),
            )
        )
    )
    acceptances_by_policy_id = {
        acceptance.policy_id: acceptance
        for acceptance in acceptances
    }

    return any(
        (acceptance := acceptances_by_policy_id.get(policy.id)) is not None
        and acceptance.policy_version == policy.version
        for policy in policies
    )


def require_marketing_access_for_agent(db: Session, current_user: User) -> None:
    agent_profile = get_own_agent_profile_or_404(db, current_user)
    if not has_accepted_social_media_policy(db, agent_profile.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Marketing Hub is locked until the social media policy has been accepted.",
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


@router.get("/marketing-assets", response_model=list[MarketingAssetRead])
def list_marketing_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[MarketingAsset]:
    query = select(MarketingAsset).order_by(MarketingAsset.asset_type, MarketingAsset.asset_name, MarketingAsset.id)
    if not is_admin_user(current_user):
        require_marketing_access_for_agent(db, current_user)
        query = query.where(MarketingAsset.visible_to_agents.is_(True))
    return list(db.scalars(query))


@router.post("/marketing-assets", response_model=MarketingAssetRead, status_code=status.HTTP_201_CREATED)
def create_marketing_asset(
    request: MarketingAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MarketingAsset:
    require_admin_user(current_user)

    marketing_asset = MarketingAsset(
        asset_name=request.asset_name,
        asset_type=request.asset_type,
        description=request.description,
        file_url=request.file_url,
        resource_url=request.resource_url,
        approved_offer_wording=request.approved_offer_wording,
        access_notes=request.access_notes,
        visible_to_agents=request.visible_to_agents,
        created_by=current_user.id,
    )
    db.add(marketing_asset)
    db.commit()
    db.refresh(marketing_asset)
    return marketing_asset
