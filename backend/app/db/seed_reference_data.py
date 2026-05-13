from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.training import (
    DEFAULT_FURTHER_TRAINING_MODULES,
    DEFAULT_MANDATORY_MODULES,
    FURTHER_TRAINING_CATEGORIES,
    FURTHER_TRAINING_TRACK,
    TRAINING_CATEGORIES,
)
from app.models.training import TrainingCategory, TrainingModule


def seed_reference_data(db: Session) -> None:
    seed_training_categories(db)
    seed_default_training_modules(db)


def seed_training_categories(db: Session) -> None:
    for name in [*TRAINING_CATEGORIES, *FURTHER_TRAINING_CATEGORIES]:
        ensure_training_category(db, name)


def seed_default_training_modules(db: Session) -> None:
    for spec in DEFAULT_MANDATORY_MODULES:
        ensure_training_module(db, spec, training_track="Onboarding")

    for spec in DEFAULT_FURTHER_TRAINING_MODULES:
        ensure_training_module(db, spec, training_track=FURTHER_TRAINING_TRACK)


def ensure_training_category(db: Session, name: str) -> TrainingCategory:
    category = db.scalar(select(TrainingCategory).where(TrainingCategory.name == name))
    if category is None:
        category = TrainingCategory(name=name, description=f"{name} training")
        db.add(category)
        db.flush()
    return category


def ensure_training_module(db: Session, spec: dict, *, training_track: str) -> TrainingModule:
    category = ensure_training_category(db, spec["category_name"])
    module = db.scalar(
        select(TrainingModule).where(
            TrainingModule.title == spec["title"],
            TrainingModule.training_track == training_track,
        )
    )
    module_data = {
        "title": spec["title"],
        "description": spec.get("description"),
        "category_id": category.id,
        "level": spec.get("level"),
        "mandatory": spec.get("mandatory", False),
        "estimated_completion_time": spec.get("estimated_completion_time"),
        "content_type": spec.get("content_type"),
        "content_url": spec.get("content_url"),
        "video_url": spec.get("video_url"),
        "pdf_url": spec.get("pdf_url"),
        "text_content": spec.get("text_content"),
        "quiz_required": spec.get("quiz_required", False),
        "pass_mark": spec.get("pass_mark"),
        "certificate_issued": spec.get("certificate_issued", False),
        "renewal_required": spec.get("renewal_required", False),
        "renewal_period_months": spec.get("renewal_period_months"),
        "expiry_date": spec.get("expiry_date"),
        "published_status": spec.get("published_status", "Published"),
        "training_track": training_track,
    }

    if module is None:
        module = TrainingModule(**module_data)
        db.add(module)
        db.flush()
        return module

    for field, value in module_data.items():
        setattr(module, field, value)
    return module
