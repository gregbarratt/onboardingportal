from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.agents import check_agent_access, get_agent_or_404, is_admin_user
from app.api.deps import get_current_active_user
from app.core.training import DEFAULT_TRAINING_PROGRESS_STATUS
from app.db.session import get_db
from app.models.agent_profile import AgentProfile
from app.models.training import (
    AgentTrainingProgress,
    TrainingAssignment,
    TrainingCategory,
    TrainingModule,
)
from app.models.user import User
from app.schemas.training import (
    AgentTrainingProgressRead,
    AgentTrainingProgressUpdate,
    TrainingAssignRequest,
    TrainingModuleCreate,
    TrainingModuleRead,
    TrainingModuleUpdate,
)


router = APIRouter(tags=["Training Academy"])


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
            )
            .order_by(TrainingModule.id)
        )
    )
    for training_module in mandatory_modules:
        ensure_training_assignment(db, agent_profile, training_module)
    db.commit()


@router.get("/training/modules", response_model=list[TrainingModuleRead])
def list_training_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrainingModule]:
    query = select(TrainingModule).options(selectinload(TrainingModule.category)).order_by(TrainingModule.id)
    if not is_admin_user(current_user):
        query = query.where(TrainingModule.published_status == "Published")
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
    return training_module


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
            .order_by(TrainingModule.id)
        )
    )


@router.put("/agents/{agent_profile_id}/training/{progress_id}", response_model=AgentTrainingProgressRead)
def update_agent_training_progress(
    agent_profile_id: int,
    progress_id: int,
    request: AgentTrainingProgressUpdate,
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

    db.commit()
    db.refresh(progress)
    return get_training_progress_or_404(db, progress.id)
