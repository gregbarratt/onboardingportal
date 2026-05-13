from sqlalchemy.orm import Session

from app.core.audit import AUDIT_ACTION_TYPES
from app.models.audit import AuditLog


def create_audit_log(
    db: Session,
    *,
    action_type: str,
    description: str,
    created_by: int | None = None,
    user_id: int | None = None,
    agent_id: int | None = None,
    previous_value: str | None = None,
    new_value: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    if action_type not in AUDIT_ACTION_TYPES:
        raise ValueError("Unsupported audit action type.")

    audit_log = AuditLog(
        user_id=user_id,
        agent_id=agent_id,
        action_type=action_type,
        description=description,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
        created_by=created_by,
    )
    db.add(audit_log)
    return audit_log
