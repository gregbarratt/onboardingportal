import base64
import binascii
import re
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.training import (
    DEFAULT_TRAINING_PROGRESS_STATUS,
    DEFAULT_TRAINING_TRACK,
    FURTHER_TRAINING_TRACK,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.training import (
    AgentTrainingProgress,
    TrainingAssignment,
    TrainingCategory,
    TrainingModule,
    TrainingQuizAnswer,
    TrainingQuizAttempt,
    TrainingQuizOption,
    TrainingQuizQuestion,
)
from app.models.user import User
from app.schemas.training import (
    AgentTrainingProgressRead,
    AgentTrainingProgressUpdate,
    TrainingCategoryCreate,
    TrainingCategoryRead,
    TrainingAssignRequest,
    TrainingMaterialUploadRequest,
    TrainingModuleCreate,
    TrainingModuleRead,
    TrainingModuleUpdate,
    TrainingQuizAttemptRead,
    TrainingQuizRead,
    TrainingQuizSaveRequest,
    TrainingQuizSubmitRequest,
    TrainingRedoRequest,
)
from app.services.certificate_generator import issue_training_certificate
from app.services.onboarding_sync import sync_agent_onboarding_progress


router = APIRouter(tags=["Training Academy"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
ALLOWED_PDF_EXTENSIONS = {".pdf"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


def clean_material_type(material_type: str) -> str:
    cleaned = material_type.strip()
    if cleaned not in {"Video", "PDF"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Training material must be a video or PDF.",
        )
    return cleaned


def get_category_or_404(db: Session, category_id: int) -> TrainingCategory:
    category = db.get(TrainingCategory, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training category not found.",
        )
    return category


def get_training_module_or_404(db: Session, module_id: int) -> TrainingModule:
    training_module = db.scalar(
        select(TrainingModule)
        .options(selectinload(TrainingModule.category))
        .where(TrainingModule.id == module_id)
    )
    if training_module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training module not found.",
        )
    return training_module


def require_admin_user(current_user: User) -> None:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage training content.",
        )


def clean_uploaded_filename(filename: str | None) -> str:
    original_name = Path(filename or "training-file").name
    cleaned_name = SAFE_FILENAME_PATTERN.sub("_", original_name).strip("._")
    return cleaned_name or "training-file"


def validate_training_material_filename(material_type: str, file_name: str | None) -> str:
    material_type = clean_material_type(material_type)
    original_file_name = clean_uploaded_filename(file_name)
    file_extension = Path(original_file_name).suffix.lower()
    allowed_extensions = (
        ALLOWED_VIDEO_EXTENSIONS if material_type == "Video" else ALLOWED_PDF_EXTENSIONS
    )

    if file_extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please upload one of these file types: {allowed}.",
        )

    return original_file_name


def build_training_material_file_target(training_module_id: int, original_file_name: str) -> tuple[Path, str]:
    module_upload_dir = settings.upload_dir / "training" / f"module-{training_module_id}"
    module_upload_dir.mkdir(parents=True, exist_ok=True)
    stored_file_name = f"{uuid4().hex}-{original_file_name}"
    target_path = module_upload_dir / stored_file_name
    public_path = f"/uploaded-files/training/module-{training_module_id}/{stored_file_name}"
    return target_path, public_path


def save_training_material_file(
    training_module_id: int,
    upload_request: TrainingMaterialUploadRequest,
) -> tuple[str, str]:
    raw_base64_content = upload_request.file_content_base64.strip()
    if raw_base64_content.startswith("data:") and "," in raw_base64_content:
        raw_base64_content = raw_base64_content.split(",", 1)[1]

    try:
        file_bytes = base64.b64decode(raw_base64_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file could not be read.",
        ) from exc

    return save_training_material_file_bytes(
        training_module_id,
        upload_request.material_type,
        upload_request.file_name,
        file_bytes,
    )


def save_training_material_file_bytes(
    training_module_id: int,
    material_type: str,
    file_name: str | None,
    file_bytes: bytes,
) -> tuple[str, str]:
    material_type = clean_material_type(material_type)
    original_file_name = validate_training_material_filename(material_type, file_name)

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Training files must be {settings.max_upload_size_mb}MB or smaller.",
        )

    target_path, public_path = build_training_material_file_target(training_module_id, original_file_name)

    try:
        target_path.write_bytes(file_bytes)
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    return original_file_name, public_path


async def save_training_material_upload_file(
    training_module_id: int,
    material_type: str,
    uploaded_file: UploadFile,
) -> tuple[str, str]:
    material_type = clean_material_type(material_type)
    original_file_name = validate_training_material_filename(material_type, uploaded_file.filename)
    target_path, public_path = build_training_material_file_target(training_module_id, original_file_name)
    bytes_written = 0

    try:
        with target_path.open("wb") as output_file:
            while True:
                chunk = await uploaded_file.read(UPLOAD_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Training files must be {settings.max_upload_size_mb}MB or smaller.",
                    )
                output_file.write(chunk)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    if bytes_written == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    return original_file_name, public_path


def build_public_file_url(request: Request, public_path: str) -> str:
    return f"{str(request.base_url).rstrip('/')}{public_path}"


def get_training_progress_or_404(db: Session, progress_id: int) -> AgentTrainingProgress:
    progress = db.scalar(
        select(AgentTrainingProgress)
        .options(
            selectinload(AgentTrainingProgress.assignment),
            selectinload(AgentTrainingProgress.training_module).selectinload(TrainingModule.category),
        )
        .where(AgentTrainingProgress.id == progress_id)
    )
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training progress item not found.",
        )
    return progress


def ensure_training_assignment(
    db: Session,
    agent_profile: AgentProfile,
    training_module: TrainingModule,
    assigned_by: int | None = None,
    due_date=None,
    mandatory: bool | None = None,
    notes: str | None = None,
) -> TrainingAssignment:
    assignment = db.scalar(
        select(TrainingAssignment).where(
            TrainingAssignment.agent_id == agent_profile.id,
            TrainingAssignment.training_module_id == training_module.id,
        )
    )
    if assignment is None:
        assignment = TrainingAssignment(
            agent_id=agent_profile.id,
            training_module_id=training_module.id,
            assigned_by=assigned_by,
            due_date=due_date,
            mandatory=training_module.mandatory if mandatory is None else mandatory,
            notes=notes,
        )
        db.add(assignment)
        db.flush()
    else:
        if due_date is not None:
            assignment.due_date = due_date
        if mandatory is not None:
            assignment.mandatory = mandatory
        if notes is not None:
            assignment.notes = notes

    progress = db.scalar(
        select(AgentTrainingProgress).where(
            AgentTrainingProgress.agent_id == agent_profile.id,
            AgentTrainingProgress.training_module_id == training_module.id,
        )
    )
    if progress is None:
        db.add(
            AgentTrainingProgress(
                assignment_id=assignment.id,
                agent_id=agent_profile.id,
                training_module_id=training_module.id,
                progress_status=DEFAULT_TRAINING_PROGRESS_STATUS,
            )
        )

    return assignment


def ensure_mandatory_training_assignments(db: Session, agent_profile: AgentProfile) -> None:
    mandatory_modules = list(
        db.scalars(
            select(TrainingModule)
            .where(
                TrainingModule.mandatory.is_(True),
                TrainingModule.published_status == "Published",
                TrainingModule.training_track == DEFAULT_TRAINING_TRACK,
            )
            .order_by(TrainingModule.id)
        )
    )
    for training_module in mandatory_modules:
        ensure_training_assignment(db, agent_profile, training_module)
    db.commit()


def ensure_mandatory_further_training_assignments(db: Session, agent_profile: AgentProfile) -> None:
    mandatory_modules = list(
        db.scalars(
            select(TrainingModule)
            .where(
                TrainingModule.mandatory.is_(True),
                TrainingModule.published_status == "Published",
                TrainingModule.training_track == FURTHER_TRAINING_TRACK,
            )
            .order_by(TrainingModule.id)
        )
    )
    for training_module in mandatory_modules:
        ensure_training_assignment(db, agent_profile, training_module)
    db.commit()


def get_own_agent_profile_or_404(db: Session, current_user: User) -> AgentProfile:
    agent_profile = db.scalar(select(AgentProfile).where(AgentProfile.user_id == current_user.id))
    if agent_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found for this user.",
        )
    return agent_profile


def get_missing_mandatory_onboarding_training(db: Session, agent_profile: AgentProfile) -> list[str]:
    ensure_mandatory_training_assignments(db, agent_profile)
    mandatory_modules = list(
        db.scalars(
            select(TrainingModule)
            .where(
                TrainingModule.mandatory.is_(True),
                TrainingModule.published_status == "Published",
                TrainingModule.training_track == DEFAULT_TRAINING_TRACK,
            )
            .order_by(TrainingModule.id)
        )
    )
    progress_records = list(
        db.scalars(
            select(AgentTrainingProgress).where(
                AgentTrainingProgress.agent_id == agent_profile.id,
                AgentTrainingProgress.training_module_id.in_([module.id for module in mandatory_modules] or [0]),
            )
        )
    )
    progress_by_module_id = {
        progress.training_module_id: progress
        for progress in progress_records
    }

    missing_modules = []
    for training_module in mandatory_modules:
        progress = progress_by_module_id.get(training_module.id)
        if progress is None or progress.progress_status != "Complete":
            missing_modules.append(training_module.title)
            continue
        if training_module.quiz_required and progress.passed is not True:
            missing_modules.append(training_module.title)
    return missing_modules


def raise_if_further_training_locked(db: Session, agent_profile: AgentProfile) -> None:
    missing_modules = get_missing_mandatory_onboarding_training(db, agent_profile)
    if missing_modules:
        missing_list = ", ".join(missing_modules)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Further training is locked until mandatory onboarding training is complete. Missing: {missing_list}.",
        )


@router.get("/training/categories", response_model=list[TrainingCategoryRead])
def list_training_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrainingCategory]:
    require_admin_user(current_user)
    return list(db.scalars(select(TrainingCategory).order_by(TrainingCategory.name)))


@router.post("/training/categories", response_model=TrainingCategoryRead, status_code=status.HTTP_201_CREATED)
def create_training_category(
    request: TrainingCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingCategory:
    require_admin_user(current_user)
    existing_category = db.scalar(select(TrainingCategory).where(TrainingCategory.name == request.name))
    if existing_category is not None:
        return existing_category

    category = TrainingCategory(name=request.name, description=request.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/training/modules", response_model=list[TrainingModuleRead])
def list_training_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrainingModule]:
    query = select(TrainingModule).options(selectinload(TrainingModule.category)).order_by(TrainingModule.id)
    if not is_admin_user(current_user):
        query = query.where(
            TrainingModule.published_status == "Published",
            TrainingModule.training_track == DEFAULT_TRAINING_TRACK,
        )
    return list(db.scalars(query))


@router.post("/training/modules", response_model=TrainingModuleRead, status_code=status.HTTP_201_CREATED)
def create_training_module(
    request: TrainingModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create training modules.",
        )

    get_category_or_404(db, request.category_id)
    training_module = TrainingModule(
        title=request.title,
        description=request.description,
        category_id=request.category_id,
        level=request.level,
        mandatory=request.mandatory,
        estimated_completion_time=request.estimated_completion_time,
        content_type=request.content_type,
        content_url=request.content_url,
        video_url=request.video_url,
        pdf_url=request.pdf_url,
        text_content=request.text_content,
        quiz_required=request.quiz_required,
        pass_mark=request.pass_mark,
        certificate_issued=request.certificate_issued,
        renewal_required=request.renewal_required,
        renewal_period_months=request.renewal_period_months,
        expiry_date=request.expiry_date,
        training_track=request.training_track,
        published_status=request.published_status,
        created_by=current_user.id,
    )
    db.add(training_module)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Training module could not be created because it conflicts with an existing record.",
        ) from None

    db.refresh(training_module)
    return get_training_module_or_404(db, training_module.id)


@router.get("/training/modules/{module_id}", response_model=TrainingModuleRead)
def get_training_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    training_module = get_training_module_or_404(db, module_id)
    if not is_admin_user(current_user) and training_module.published_status != "Published":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This training module is not published.",
        )
    if not is_admin_user(current_user) and training_module.training_track == FURTHER_TRAINING_TRACK:
        agent_profile = get_own_agent_profile_or_404(db, current_user)
        raise_if_further_training_locked(db, agent_profile)
    return training_module


@router.post("/training/modules/{module_id}/materials", response_model=TrainingModuleRead)
async def upload_training_material(
    module_id: int,
    http_request: Request,
    material_type: str = Form(...),
    uploaded_file: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    require_admin_user(current_user)
    training_module = get_training_module_or_404(db, module_id)
    material_type = clean_material_type(material_type)
    try:
        _file_name, public_path = await save_training_material_upload_file(module_id, material_type, uploaded_file)
    finally:
        await uploaded_file.close()
    file_url = build_public_file_url(http_request, public_path)

    if material_type == "Video":
        training_module.video_url = file_url
    else:
        training_module.pdf_url = file_url

    if training_module.video_url and training_module.pdf_url:
        training_module.content_type = "Mixed"
    else:
        training_module.content_type = material_type

    db.commit()
    db.refresh(training_module)
    return get_training_module_or_404(db, training_module.id)


def load_quiz_questions(db: Session, module_id: int) -> list[TrainingQuizQuestion]:
    return list(
        db.scalars(
            select(TrainingQuizQuestion)
            .options(selectinload(TrainingQuizQuestion.options))
            .where(TrainingQuizQuestion.training_module_id == module_id)
            .order_by(TrainingQuizQuestion.sort_order)
        )
    )


def validate_quiz_questions(request: TrainingQuizSaveRequest) -> None:
    for index, question in enumerate(request.questions, start=1):
        if len(question.options) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {index} needs at least two answer options.",
            )
        if not any(option.is_correct for option in question.options):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {index} needs one correct answer.",
            )


@router.get("/training/modules/{module_id}/quiz", response_model=TrainingQuizRead)
def get_training_quiz(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    training_module = get_training_module_or_404(db, module_id)
    if not is_admin_user(current_user) and training_module.published_status != "Published":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This training module is not published.",
        )
    if not is_admin_user(current_user) and training_module.training_track == FURTHER_TRAINING_TRACK:
        agent_profile = get_own_agent_profile_or_404(db, current_user)
        raise_if_further_training_locked(db, agent_profile)

    questions = load_quiz_questions(db, module_id)
    if not is_admin_user(current_user):
        questions = [
            {
                "id": question.id,
                "training_module_id": question.training_module_id,
                "question_text": question.question_text,
                "sort_order": question.sort_order,
                "options": [
                    {
                        "id": option.id,
                        "question_id": option.question_id,
                        "option_text": option.option_text,
                        "is_correct": False,
                        "sort_order": option.sort_order,
                    }
                    for option in question.options
                ],
            }
            for question in questions
        ]

    return {
        "training_module_id": training_module.id,
        "pass_mark": training_module.pass_mark,
        "quiz_required": training_module.quiz_required,
        "questions": questions,
    }


@router.put("/training/modules/{module_id}/quiz", response_model=TrainingQuizRead)
def save_training_quiz(
    module_id: int,
    request: TrainingQuizSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    require_admin_user(current_user)
    training_module = get_training_module_or_404(db, module_id)
    validate_quiz_questions(request)

    for existing_question in load_quiz_questions(db, module_id):
        db.delete(existing_question)
    db.flush()

    for question_index, question in enumerate(request.questions, start=1):
        quiz_question = TrainingQuizQuestion(
            training_module_id=training_module.id,
            question_text=question.question_text,
            sort_order=question_index,
        )
        db.add(quiz_question)
        db.flush()

        for option_index, option in enumerate(question.options, start=1):
            db.add(
                TrainingQuizOption(
                    question_id=quiz_question.id,
                    option_text=option.option_text,
                    is_correct=option.is_correct,
                    sort_order=option_index,
                )
            )

    training_module.quiz_required = bool(request.questions)
    if training_module.quiz_required and training_module.pass_mark is None:
        training_module.pass_mark = 80

    db.commit()
    return {
        "training_module_id": training_module.id,
        "pass_mark": training_module.pass_mark,
        "quiz_required": training_module.quiz_required,
        "questions": load_quiz_questions(db, module_id),
    }


@router.put("/training/modules/{module_id}", response_model=TrainingModuleRead)
def update_training_module(
    module_id: int,
    request: TrainingModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update training modules.",
        )

    training_module = get_training_module_or_404(db, module_id)
    update_data = request.model_dump(exclude_unset=True)
    if "category_id" in update_data and update_data["category_id"] is not None:
        get_category_or_404(db, update_data["category_id"])

    for field, value in update_data.items():
        setattr(training_module, field, value)

    db.commit()
    db.refresh(training_module)
    return get_training_module_or_404(db, training_module.id)


@router.post("/training/modules/{module_id}/publish", response_model=TrainingModuleRead)
def publish_training_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can publish training modules.",
        )

    training_module = get_training_module_or_404(db, module_id)
    training_module.published_status = "Published"
    db.commit()
    db.refresh(training_module)
    return get_training_module_or_404(db, training_module.id)


@router.post("/training/modules/{module_id}/archive", response_model=TrainingModuleRead)
def archive_training_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingModule:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can archive training modules.",
        )

    training_module = get_training_module_or_404(db, module_id)
    training_module.published_status = "Archived"
    db.commit()
    db.refresh(training_module)
    return get_training_module_or_404(db, training_module.id)


@router.post("/training/modules/{module_id}/assign", response_model=AgentTrainingProgressRead)
def assign_training_module(
    module_id: int,
    request: TrainingAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentTrainingProgress:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign training modules.",
        )

    training_module = get_training_module_or_404(db, module_id)
    agent_profile = get_agent_or_404(db, request.agent_id)
    check_agent_access(agent_profile, current_user)
    ensure_training_assignment(
        db,
        agent_profile,
        training_module,
        assigned_by=current_user.id,
        due_date=request.due_date,
        mandatory=request.mandatory,
        notes=request.notes,
    )
    db.commit()

    progress = db.scalar(
        select(AgentTrainingProgress)
        .options(
            selectinload(AgentTrainingProgress.assignment),
            selectinload(AgentTrainingProgress.training_module).selectinload(TrainingModule.category),
        )
        .where(
            AgentTrainingProgress.agent_id == agent_profile.id,
            AgentTrainingProgress.training_module_id == training_module.id,
        )
    )
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Training assignment was created but could not be loaded.",
        )
    return progress


@router.get("/agents/{agent_profile_id}/training", response_model=list[AgentTrainingProgressRead])
def list_agent_training(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AgentTrainingProgress]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    ensure_mandatory_training_assignments(db, agent_profile)
    return list(
        db.scalars(
            select(AgentTrainingProgress)
            .options(
                selectinload(AgentTrainingProgress.assignment),
                selectinload(AgentTrainingProgress.training_module).selectinload(TrainingModule.category),
            )
            .where(AgentTrainingProgress.agent_id == agent_profile.id)
            .join(TrainingModule)
            .where(TrainingModule.training_track == DEFAULT_TRAINING_TRACK)
            .order_by(TrainingModule.id)
        )
    )


def get_agent_module_progress(
    db: Session,
    agent_profile: AgentProfile,
    training_module: TrainingModule,
) -> AgentTrainingProgress:
    ensure_training_assignment(db, agent_profile, training_module)
    db.commit()
    progress = db.scalar(
        select(AgentTrainingProgress).where(
            AgentTrainingProgress.agent_id == agent_profile.id,
            AgentTrainingProgress.training_module_id == training_module.id,
        )
    )
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Training progress could not be loaded.",
        )
    return progress


@router.get("/training/modules/{module_id}/quiz/attempts", response_model=list[TrainingQuizAttemptRead])
def list_my_training_quiz_attempts(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrainingQuizAttempt]:
    training_module = get_training_module_or_404(db, module_id)
    agent_profile = get_own_agent_profile_or_404(db, current_user)
    if training_module.training_track == FURTHER_TRAINING_TRACK:
        raise_if_further_training_locked(db, agent_profile)

    return list(
        db.scalars(
            select(TrainingQuizAttempt)
            .options(selectinload(TrainingQuizAttempt.answers))
            .where(
                TrainingQuizAttempt.agent_id == agent_profile.id,
                TrainingQuizAttempt.training_module_id == training_module.id,
            )
            .order_by(TrainingQuizAttempt.attempt_number.desc())
        )
    )


@router.post("/training/modules/{module_id}/quiz/attempts", response_model=TrainingQuizAttemptRead)
def submit_training_quiz_attempt(
    module_id: int,
    request: TrainingQuizSubmitRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrainingQuizAttempt:
    training_module = get_training_module_or_404(db, module_id)
    agent_profile = get_own_agent_profile_or_404(db, current_user)
    if training_module.training_track == FURTHER_TRAINING_TRACK:
        raise_if_further_training_locked(db, agent_profile)

    questions = load_quiz_questions(db, training_module.id)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This module does not have a quiz yet.",
        )

    selected_by_question_id = {
        answer.question_id: answer.selected_option_id
        for answer in request.answers
    }
    missing_questions = [question for question in questions if question.id not in selected_by_question_id]
    if missing_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please answer every quiz question before submitting.",
        )

    correct_count = 0
    answers_to_create = []
    for question in questions:
        option_by_id = {option.id: option for option in question.options}
        selected_option = option_by_id.get(selected_by_question_id[question.id])
        if selected_option is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the selected answers does not belong to this quiz.",
            )
        is_correct = selected_option.is_correct
        correct_count += 1 if is_correct else 0
        answers_to_create.append((question.id, selected_option.id, is_correct))

    score = round((correct_count / len(questions)) * 100)
    pass_mark = training_module.pass_mark or 80
    passed = score >= pass_mark
    progress = get_agent_module_progress(db, agent_profile, training_module)

    previous_attempt_count = db.scalar(
        select(func.count(TrainingQuizAttempt.id)).where(
            TrainingQuizAttempt.agent_id == agent_profile.id,
            TrainingQuizAttempt.training_module_id == training_module.id,
        )
    ) or 0
    attempt = TrainingQuizAttempt(
        agent_id=agent_profile.id,
        training_module_id=training_module.id,
        progress_id=progress.id,
        attempt_number=previous_attempt_count + 1,
        score=score,
        passed=passed,
        status="Passed" if passed else "Failed",
    )
    db.add(attempt)
    db.flush()

    for question_id, selected_option_id, is_correct in answers_to_create:
        db.add(
            TrainingQuizAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                is_correct=is_correct,
            )
        )

    if progress.started_date is None:
        progress.started_date = date.today()
    progress.score = score
    progress.passed = passed
    progress.progress_status = "Complete" if passed else "Failed"
    progress.completed_date = date.today() if passed else None
    if passed:
        certificate = issue_training_certificate(
            db,
            agent_profile,
            training_module,
            public_base_url=str(http_request.base_url).rstrip("/"),
        )
        if certificate is not None:
            progress.expiry_date = certificate.expiry_date
            progress.certificate_issued = True

    db.flush()
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)
    db.commit()
    return db.scalar(
        select(TrainingQuizAttempt)
        .options(selectinload(TrainingQuizAttempt.answers))
        .where(TrainingQuizAttempt.id == attempt.id)
    )


@router.put("/agents/{agent_profile_id}/training/{progress_id}", response_model=AgentTrainingProgressRead)
def update_agent_training_progress(
    agent_profile_id: int,
    progress_id: int,
    request: AgentTrainingProgressUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentTrainingProgress:
    agent_profile: AgentProfile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    progress = get_training_progress_or_404(db, progress_id)

    if progress.agent_id != agent_profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training progress item not found for this agent.",
        )

    admin_user = is_admin_user(current_user)
    update_data = request.model_dump(exclude_unset=True)
    admin_only_fields = {"score", "passed", "certificate_issued", "expiry_date"}
    if not admin_user and admin_only_fields.intersection(update_data):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update training scores, pass results, and certificates.",
        )

    if not admin_user and progress.training_module.training_track == FURTHER_TRAINING_TRACK:
        raise_if_further_training_locked(db, agent_profile)

    if "progress_status" in update_data and update_data["progress_status"] == "In Progress":
        if update_data.get("started_date") is None and progress.started_date is None:
            progress.started_date = date.today()

    if "progress_status" in update_data and update_data["progress_status"] == "Complete":
        if update_data.get("completed_date") is None and progress.completed_date is None:
            progress.completed_date = date.today()
        if progress.training_module.quiz_required and not admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This training module needs admin review before it can be completed.",
            )

    for field, value in update_data.items():
        setattr(progress, field, value)

    if progress.progress_status == "Complete":
        certificate = issue_training_certificate(
            db,
            agent_profile,
            progress.training_module,
            public_base_url=str(http_request.base_url).rstrip("/"),
        )
        if certificate is not None:
            progress.certificate_issued = True
            progress.expiry_date = certificate.expiry_date

    db.flush()
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)
    db.commit()
    db.refresh(progress)
    return get_training_progress_or_404(db, progress.id)


@router.post("/agents/{agent_profile_id}/training/{progress_id}/redo", response_model=AgentTrainingProgressRead)
def request_training_redo(
    agent_profile_id: int,
    progress_id: int,
    request: TrainingRedoRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AgentTrainingProgress:
    require_admin_user(current_user)
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    progress = get_training_progress_or_404(db, progress_id)
    if progress.agent_id != agent_profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training progress item not found for this agent.",
        )

    progress.progress_status = "In Progress"
    progress.completed_date = None
    progress.passed = False
    if request is not None and request.notes:
        progress.notes = request.notes

    latest_attempt = db.scalar(
        select(TrainingQuizAttempt)
        .where(
            TrainingQuizAttempt.agent_id == agent_profile.id,
            TrainingQuizAttempt.training_module_id == progress.training_module_id,
        )
        .order_by(TrainingQuizAttempt.attempt_number.desc())
    )
    if latest_attempt is not None:
        latest_attempt.status = "Redo Requested"
        latest_attempt.redo_requested_by = current_user.id
        latest_attempt.redo_requested_date = datetime.now(timezone.utc)
        if request is not None and request.notes:
            latest_attempt.admin_notes = request.notes

    db.flush()
    sync_agent_onboarding_progress(db, agent_profile, actor_user_id=current_user.id)
    db.commit()
    db.refresh(progress)
    return get_training_progress_or_404(db, progress.id)


@router.get("/further-training", response_model=list[TrainingModuleRead])
def list_further_training_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrainingModule]:
    if not is_admin_user(current_user):
        agent_profile = get_own_agent_profile_or_404(db, current_user)
        raise_if_further_training_locked(db, agent_profile)

    query = (
        select(TrainingModule)
        .options(selectinload(TrainingModule.category))
        .where(TrainingModule.training_track == FURTHER_TRAINING_TRACK)
        .order_by(TrainingModule.id)
    )
    if not is_admin_user(current_user):
        query = query.where(TrainingModule.published_status == "Published")
    return list(db.scalars(query))


@router.get("/agents/{agent_profile_id}/further-training", response_model=list[AgentTrainingProgressRead])
def list_agent_further_training(
    agent_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AgentTrainingProgress]:
    agent_profile = get_agent_or_404(db, agent_profile_id)
    check_agent_access(agent_profile, current_user)
    raise_if_further_training_locked(db, agent_profile)
    ensure_mandatory_further_training_assignments(db, agent_profile)
    return list(
        db.scalars(
            select(AgentTrainingProgress)
            .options(
                selectinload(AgentTrainingProgress.assignment),
                selectinload(AgentTrainingProgress.training_module).selectinload(TrainingModule.category),
            )
            .join(TrainingModule)
            .where(
                AgentTrainingProgress.agent_id == agent_profile.id,
                TrainingModule.training_track == FURTHER_TRAINING_TRACK,
            )
            .order_by(TrainingModule.id)
        )
    )
