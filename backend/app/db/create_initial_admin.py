from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import DEFAULT_ROLES
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User
from app.services.passwords import hash_password


def ensure_roles(db: Session) -> dict[str, Role]:
    role_names = [name for name, _ in DEFAULT_ROLES]
    existing_roles = {
        role.name: role
        for role in db.scalars(select(Role).where(Role.name.in_(role_names)))
    }

    for name, description in DEFAULT_ROLES:
        if name not in existing_roles:
            role = Role(name=name, description=description)
            db.add(role)
            existing_roles[name] = role

    db.flush()
    return existing_roles


def create_initial_admin() -> None:
    email = settings.initial_admin_email.strip().lower()
    password = settings.initial_admin_password

    if not email or not password:
        if settings.environment == "production":
            raise RuntimeError(
                "INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD must be set before deployment."
            )
        print("Initial admin was not created because no admin email/password was set.")
        return

    with SessionLocal() as db:
        roles = ensure_roles(db)
        existing_user = db.scalar(select(User).where(User.email == email))

        if existing_user is not None:
            print(f"Initial admin already exists: {email}")
            return

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role=roles["Super Admin"],
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Initial admin created: {email}")


if __name__ == "__main__":
    create_initial_admin()
