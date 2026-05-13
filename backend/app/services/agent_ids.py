import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_profile import AgentProfile


AGENT_ID_PREFIX = "OTC-"
AGENT_ID_PATTERN = re.compile(r"^OTC-(\d+)$")


def generate_next_agent_id(db: Session) -> str:
    highest_number = 0
    agent_ids = db.scalars(select(AgentProfile.agent_id)).all()

    for agent_id in agent_ids:
        match = AGENT_ID_PATTERN.match(agent_id or "")
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return f"{AGENT_ID_PREFIX}{highest_number + 1:05d}"
