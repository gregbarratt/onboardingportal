import base64
import binascii
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.documents import DEFAULT_DOCUMENT_STATUS
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentFileUploadCreate, DocumentRead, DocumentReviewRequest


router = APIRouter(tags=["Documents and Agreements"])

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


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


def clean_uploaded_filename(filename: str | None) -> str:
    original_name = Path(filename or "document").name
    cleaned_name = SAFE_FILENAME_PATTERN.sub("_", original_name).strip("._")
    return cleaned_name or "document"


def save_uploaded_document_file(agent_profile_id: int, file_name: str, file_content_base64: str) -> tuple[str, str]:
    original_file_name = clean_uploaded_filename(file_name)
    file_extension = Path(original_file_name).suffix.lower()

    if file_extension not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please upload one of these file types: {allowed}.",
        )

    raw_base64_content = file_content_base64.strip()
    if raw_base64_content.startswith("data:") and "," in raw_base64_content:
        raw_base64_content = raw_base64_content.split(",", 1)[1]

    try:
        file_bytes = base64.b64decode(raw_base64_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file could not be read.",
        ) from exc

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document files must be {settings.max_upload_size_mb}MB or smaller.",
        )

    agent_upload_dir = settings.upload_dir / "documents" / f"agent-{agent_profile_id}"
    agent_upload_dir.mkdir(parents=True, exist_ok=True)
    stored_file_name = f"{uuid4().hex}-{original_file_name}"
    target_path = agent_upload_dir / stored_file_name

    try:
        target_path.write_bytes(file_bytes)
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    public_path = f"/uploaded-files/documents/agent-{agent_profile_id}/{stored_file_name}"
    return original_file_name, public_path


def build_public_file_url(request: Request, public_path: str) -> str:
    return f"{str(request.base_url).rstrip('/')}{public_path}"


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


@router.post("/agents/{agent_profile_id}/documents/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_agent_document(
    agent_profile_id: int,
    upload_request: DocumentFileUploadCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)

    file_name, public_path = save_uploaded_document_file(
        agent_profile.id,
        upload_request.file_name,
        upload_request.file_content_base64,
    )
    file_url = build_public_file_url(http_request, public_path)

    document = Document(
        agent_id=agent_profile.id,
        document_type=upload_request.document_type,
        file_name=file_name,
        file_url=file_url,
        uploaded_by=current_user.id,
        uploaded_date=date.today(),
        requires_signature=upload_request.requires_signature,
        signed=upload_request.signed,
        signed_date=upload_request.signed_date,
        expiry_date=upload_request.expiry_date,
        status=DEFAULT_DOCUMENT_STATUS,
        notes=upload_request.notes,
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
