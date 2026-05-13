from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.certificate import Certificate
from app.models.training import TrainingModule
from app.models.user import User
from app.schemas.certificate import CertificateCreate, CertificateRead


router = APIRouter(tags=["Certificates"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create, expire, or revoke certificates.",
        )


def get_certificate_or_404(db: Session, certificate_id: int) -> Certificate:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )
    return certificate


def get_training_module_or_404(db: Session, training_module_id: int) -> TrainingModule:
    training_module = db.get(TrainingModule, training_module_id)
    if training_module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training module not found.",
        )
    return training_module


@router.get("/agents/{agent_profile_id}/certificates", response_model=list[CertificateRead])
def list_agent_certificates(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Certificate]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return list(
        db.scalars(
            select(Certificate)
            .where(Certificate.agent_id == agent_profile.id)
            .order_by(Certificate.issued_date.desc(), Certificate.id.desc())
        )
    )


@router.post("/agents/{agent_profile_id}/certificates", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
def create_agent_certificate(
    agent_profile_id: int,
    request: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Certificate:
    require_admin_user(current_user)
    agent_profile = get_agent_or_404(db, agent_profile_id)
    get_training_module_or_404(db, request.training_module_id)

    certificate = Certificate(
        agent_id=agent_profile.id,
        training_module_id=request.training_module_id,
        certificate_name=request.certificate_name,
        certificate_url=request.certificate_url,
        issued_date=request.issued_date or date.today(),
        expiry_date=request.expiry_date,
        renewal_required=request.renewal_required,
        status="Active",
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


@router.post("/certificates/{certificate_id}/expire", response_model=CertificateRead)
def expire_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Certificate:
    require_admin_user(current_user)
    certificate = get_certificate_or_404(db, certificate_id)
    certificate.status = "Expired"
    if certificate.expiry_date is None:
        certificate.expiry_date = date.today()
    db.commit()
    db.refresh(certificate)
    return certificate


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateRead)
def revoke_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Certificate:
    require_admin_user(current_user)
    certificate = get_certificate_or_404(db, certificate_id)
    certificate.status = "Revoked"
    db.commit()
    db.refresh(certificate)
    return certificate
