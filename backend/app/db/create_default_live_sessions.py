from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.live_training import LiveTrainingSession


DEFAULT_LIVE_CALL_HOST = "Nikki Bishop"
LEGACY_LIVE_CALL_HOSTS = {"Training Manager", "Compliance Manager", "Admin"}


@dataclass(frozen=True)
class DefaultLiveSession:
    title: str
    session_type: str
    description: str
    week_number: int
    session_number: int
    start_time: time
    end_time: time
    trainer_host: str
    attendance_required: bool = True
    follow_up_quiz_required: bool = False
    certificate_issued: bool = False
    notes: str = "Default onboarding programme call."


DEFAULT_ONBOARDING_LIVE_SESSIONS = (
    DefaultLiveSession(
        title="Week 1 - Session 1: Qualifying Customers and the Main Three",
        session_type="Sales Process Call",
        description=(
            "Topics covered: how to qualify your customer; introduction to the main three, "
            "what they offer, and how communications work."
        ),
        week_number=1,
        session_number=1,
        start_time=time(10, 0),
        end_time=time(11, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
    ),
    DefaultLiveSession(
        title="Week 1 - Session 2: Smart Quote, Service Standards and Disney",
        session_type="Systems Training Call",
        description=(
            "Topics covered: recap on communications; Smart Quote; what good customer "
            "service looks like; quick overview of Disney."
        ),
        week_number=1,
        session_number=2,
        start_time=time(14, 0),
        end_time=time(15, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
    ),
    DefaultLiveSession(
        title="Week 2 - Session 1: ATOL, GDPR, Hub and Business Basics",
        session_type="Compliance Call",
        description=(
            "Topics covered: ATOL; GDPR; the hub; OTC website; running a business."
        ),
        week_number=2,
        session_number=1,
        start_time=time(10, 0),
        end_time=time(11, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
        follow_up_quiz_required=True,
    ),
    DefaultLiveSession(
        title="Week 2 - Session 2: Marketing, Socials, Signs and CRM",
        session_type="Marketing Call",
        description=(
            "Topics covered: marketing and compliance; socials; signs; CRM."
        ),
        week_number=2,
        session_number=2,
        start_time=time(14, 0),
        end_time=time(15, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
    ),
    DefaultLiveSession(
        title="Week 3 - Session 1: Agent Behaviour and Client Growth",
        session_type="Sales Process Call",
        description=(
            "Topics covered: agent behaviour; growing your client base; networking; "
            "finding your niche."
        ),
        week_number=3,
        session_number=1,
        start_time=time(10, 0),
        end_time=time(11, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
    ),
    DefaultLiveSession(
        title="Week 3 - Session 2: Repackaging and Cruise Introduction",
        session_type="Supplier Training",
        description="Topics covered: introduction to repackaging and cruise.",
        week_number=3,
        session_number=2,
        start_time=time(14, 0),
        end_time=time(15, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
    ),
    DefaultLiveSession(
        title="Week 4 - Session 1: Test, OTC Facebook, Clinton and Logins",
        session_type="Final Sign-Off Call",
        description="Topics covered: the test; OTC Facebook; Clinton; logins.",
        week_number=4,
        session_number=1,
        start_time=time(10, 0),
        end_time=time(11, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
        follow_up_quiz_required=True,
    ),
    DefaultLiveSession(
        title="Week 4 - Session 2: Retake Test and Open Session",
        session_type="Final Sign-Off Call",
        description="Topics covered: retake test and open session.",
        week_number=4,
        session_number=2,
        start_time=time(14, 0),
        end_time=time(15, 30),
        trainer_host=DEFAULT_LIVE_CALL_HOST,
        follow_up_quiz_required=True,
    ),
)


def next_monday(reference_date: date | None = None) -> date:
    today = reference_date or date.today()
    days_until_monday = (0 - today.weekday()) % 7
    return today + timedelta(days=days_until_monday)


def session_date_for(spec: DefaultLiveSession, start_date: date | None = None) -> date:
    week_start = next_monday(start_date) + timedelta(weeks=spec.week_number - 1)
    if spec.session_number == 1:
        return week_start
    return week_start + timedelta(days=3)


def session_identity_prefix(title: str) -> str:
    return title.split(":", 1)[0].strip()


def ensure_default_live_sessions(db: Session) -> dict[str, int]:
    created = 0
    updated = 0

    for spec in DEFAULT_ONBOARDING_LIVE_SESSIONS:
        live_session = db.scalar(select(LiveTrainingSession).where(LiveTrainingSession.title == spec.title))
        if live_session is None:
            prefix = session_identity_prefix(spec.title).lower()
            live_session = db.scalar(
                select(LiveTrainingSession)
                .where(func.lower(LiveTrainingSession.title).like(f"{prefix}%"))
                .order_by(LiveTrainingSession.id)
                .limit(1)
            )

        if live_session is None:
            live_session = LiveTrainingSession(
                title=spec.title,
                session_type=spec.session_type,
                description=spec.description,
                date=session_date_for(spec),
                start_time=spec.start_time,
                end_time=spec.end_time,
                trainer_host=spec.trainer_host,
                attendance_required=spec.attendance_required,
                follow_up_quiz_required=spec.follow_up_quiz_required,
                certificate_issued=spec.certificate_issued,
                notes=spec.notes,
            )
            db.add(live_session)
            created += 1
            continue

        if not live_session.session_type:
            live_session.session_type = spec.session_type
        if not live_session.description:
            live_session.description = spec.description
        if live_session.attendance_required is None:
            live_session.attendance_required = spec.attendance_required
        if live_session.follow_up_quiz_required is None:
            live_session.follow_up_quiz_required = spec.follow_up_quiz_required
        if live_session.certificate_issued is None:
            live_session.certificate_issued = spec.certificate_issued
        if not live_session.notes:
            live_session.notes = spec.notes

        if live_session.start_time is None:
            live_session.start_time = spec.start_time
        if live_session.end_time is None:
            live_session.end_time = spec.end_time
        if not live_session.trainer_host or live_session.trainer_host in LEGACY_LIVE_CALL_HOSTS:
            live_session.trainer_host = spec.trainer_host

        updated += 1

    return {"created": created, "updated": updated}


def create_default_live_sessions() -> None:
    with SessionLocal() as db:
        result = ensure_default_live_sessions(db)
        db.commit()

    print(
        "Default onboarding live sessions are ready. "
        f"Created: {result['created']}. Updated: {result['updated']}."
    )


if __name__ == "__main__":
    create_default_live_sessions()
