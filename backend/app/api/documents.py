from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.documents import DEFAULT_DOCUMENT_STATUS
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead, DocumentReviewRequest


router = APIRouter(tags=["Documents and Agreements"])


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can verify or reject documents.",
        )


def get_document_or_404(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


@router.post("/agents/{agent_profile_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_agent_document(
    agent_profile_id: int,
    request: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    document = Document(
        agent_id=agent_profile.id,
        document_type=request.document_type,
        file_name=request.file_name,
        file_url=request.file_url,
        uploaded_by=current_user.id,
        uploaded_date=date.today(),
        requires_signature=request.requires_signature,
        signed=request.signed,
        signed_date=request.signed_date,
        expiry_date=request.expiry_date,
        status=DEFAULT_DOCUMENT_STATUS,
        notes=request.notes,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/agents/{agent_profile_id}/documents", response_model=list[DocumentRead])
def list_agent_documents(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Document]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    return list(
        db.scalars(
            select(Document)
            .where(Document.agent_id == agent_profile.id)
            .order_by(Document.uploaded_date.desc(), Document.id.desc())
        )
    )


@router.post("/documents/{document_id}/verify", response_model=DocumentRead)
def verify_document(
    document_id: int,
    request: DocumentReviewRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    require_admin_user(current_user)
    document = get_document_or_404(db, document_id)
    document.verified = True
    document.verified_by = current_user.id
    document.verified_date = date.today()
    document.status = "Verified"
    if request is not None and request.notes is not None:
        document.notes = request.notes

    db.commit()
    db.refresh(document)
    return document


@router.post("/documents/{document_id}/reject", response_model=DocumentRead)
def reject_document(
    document_id: int,
    request: DocumentReviewRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    require_admin_user(current_user)
    document = get_document_or_404(db, document_id)
    document.verified = False
    document.verified_by = current_user.id
    document.verified_date = date.today()
    document.status = "Rejected"
    if request is not None and request.notes is not None:
        document.notes = request.notes

    db.commit()
    db.refresh(document)
    return document
