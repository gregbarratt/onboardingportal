from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.audit import AUDIT_ACTION_TYPES
from app.core.compliance import DEFAULT_COMPLIANCE_POLICIES
from app.core.onboarding_statuses import DEFAULT_ONBOARDING_STEPS
from app.core.roles import DEFAULT_ROLES
from app.core.training import (
    DEFAULT_FURTHER_TRAINING_MODULES,
    DEFAULT_MANDATORY_MODULES,
    FURTHER_TRAINING_TRACK,
)
from app.db.base import Base
from app.db.create_default_live_sessions import ensure_default_live_sessions
from app.db.session import SessionLocal, engine
from app.models import (
    AgentOnboardingProgress,
    AgentProfile,
    AgentTrainingProgress,
    AttendanceLog,
    AuditLog,
    Certificate,
    CompliancePolicy,
    Document,
    LiveTrainingSession,
    Membership,
    OnboardingStep,
    Payment,
    PolicyAcceptance,
    Role,
    TrainingAssignment,
    TrainingCategory,
    TrainingModule,
    User,
)
from app.services.organizations import ensure_default_organization
from app.services.passwords import hash_password


DEMO_PASSWORD = "Password123!"


def seed_demo_data() -> None:
    register_sqlite_now_function()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        roles = ensure_roles(db)
        organization = ensure_default_organization(db)
        users = ensure_demo_users(db, roles, organization_id=organization.id)
        ensure_default_onboarding_steps(db)
        training_modules = ensure_default_training(db)
        policies = ensure_default_compliance_policies(db)

        agents = ensure_demo_agents(db, users, organization_id=organization.id)
        ensure_demo_memberships_and_payments(db, agents)
        ensure_demo_documents(db, agents, users["admin"])
        ensure_demo_onboarding(db, agents, users["admin"])
        ensure_demo_training_progress(db, agents, training_modules, users["training"])
        ensure_demo_policy_acceptances(db, agents, policies, users["compliance"])
        ensure_default_live_sessions(db)
        sessions = ensure_demo_live_sessions(db)
        ensure_demo_attendance(db, agents, sessions, users["training"])
        ensure_demo_certificates(db, agents, training_modules)
        ensure_demo_audit_logs(db, agents, users)

        db.commit()

    print("Demo data is ready.")
    print("Shared demo password:", DEMO_PASSWORD)
    print("Staff logins:")
    print("  superadmin@example.com")
    print("  admin@example.com")
    print("  training@example.com")
    print("  compliance@example.com")
    print("Agent logins:")
    print("  sarah.jones@example.com")
    print("  mark.evans@example.com")
    print("  emma.clarke@example.com")
    print("  david.smith@example.com")
    print("  rachel.brown@example.com")


def register_sqlite_now_function() -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def add_sqlite_now_function(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function("now", 0, lambda: datetime.utcnow().isoformat(sep=" "))


def ensure_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, description in DEFAULT_ROLES:
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
        else:
            role.description = description
        roles[name] = role
    return roles


def ensure_demo_users(db: Session, roles: dict[str, Role], *, organization_id: int) -> dict[str, User]:
    user_specs = {
        "superadmin": ("superadmin@example.com", "Super Admin"),
        "admin": ("admin@example.com", "Admin"),
        "training": ("training@example.com", "Training Manager"),
        "compliance": ("compliance@example.com", "Compliance Manager"),
        "sarah": ("sarah.jones@example.com", "Agent"),
        "mark": ("mark.evans@example.com", "Agent"),
        "emma": ("emma.clarke@example.com", "Agent"),
        "david": ("david.smith@example.com", "Agent"),
        "rachel": ("rachel.brown@example.com", "Agent"),
    }

    users: dict[str, User] = {}
    for key, (email, role_name) in user_specs.items():
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                role_id=roles[role_name].id,
                organization_id=organization_id,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.hashed_password = hash_password(DEMO_PASSWORD)
            user.role_id = roles[role_name].id
            user.organization_id = organization_id
            user.is_active = True
        users[key] = user
    return users


def ensure_default_onboarding_steps(db: Session) -> dict[str, OnboardingStep]:
    steps: dict[str, OnboardingStep] = {}
    for spec in DEFAULT_ONBOARDING_STEPS:
        step = db.scalar(select(OnboardingStep).where(OnboardingStep.sort_order == spec["sort_order"]))
        if step is None:
            step = OnboardingStep(**spec)
            db.add(step)
            db.flush()
        else:
            step.title = spec["title"]
            step.description = spec["description"]
            step.required = spec["required"]
            step.approval_required = spec["approval_required"]
        steps[step.title] = step
    return steps


def ensure_default_training(db: Session) -> dict[str, TrainingModule]:
    modules: dict[str, TrainingModule] = {}
    for spec in DEFAULT_MANDATORY_MODULES:
        module = ensure_training_module(db, spec, training_track="Onboarding")
        modules[module.title] = module

    for spec in DEFAULT_FURTHER_TRAINING_MODULES:
        module = ensure_training_module(db, spec, training_track=FURTHER_TRAINING_TRACK)
        modules[module.title] = module

    return modules


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
    else:
        for field, value in module_data.items():
            setattr(module, field, value)

    return module


def ensure_training_category(db: Session, name: str) -> TrainingCategory:
    category = db.scalar(select(TrainingCategory).where(TrainingCategory.name == name))
    if category is None:
        category = TrainingCategory(name=name, description=f"{name} training")
        db.add(category)
        db.flush()
    return category


def ensure_default_compliance_policies(db: Session) -> dict[str, CompliancePolicy]:
    policies: dict[str, CompliancePolicy] = {}
    for spec in DEFAULT_COMPLIANCE_POLICIES:
        policy = db.scalar(select(CompliancePolicy).where(CompliancePolicy.policy_type == spec["policy_type"]))
        if policy is None:
            policy = CompliancePolicy(**spec)
            db.add(policy)
            db.flush()
        else:
            policy.title = spec["title"]
            policy.content = spec["content"]
            policy.version = spec["version"]
            policy.requires_acceptance = spec["requires_acceptance"]
            policy.published_status = spec["published_status"]
        policies[policy.policy_type] = policy
    return policies


def ensure_demo_agents(db: Session, users: dict[str, User], *, organization_id: int) -> dict[str, AgentProfile]:
    agent_specs = {
        "sarah": {
            "user": users["sarah"],
            "agent_id": "OTC-DEMO-001",
            "first_name": "Sarah",
            "last_name": "Jones",
            "email": "sarah.jones@example.com",
            "phone": "07123 000001",
            "business_name": "Sarah Jones Travel",
            "status": "Onboarding In Progress",
            "address": "12 Harbour Road, Manchester",
            "postcode": "M1 1AA",
        },
        "mark": {
            "user": users["mark"],
            "agent_id": "OTC-DEMO-002",
            "first_name": "Mark",
            "last_name": "Evans",
            "email": "mark.evans@example.com",
            "phone": "07123 000002",
            "business_name": "Mark Evans Holidays",
            "status": "Payment Pending",
            "address": "44 Station Lane, Birmingham",
            "postcode": "B1 2BB",
        },
        "emma": {
            "user": users["emma"],
            "agent_id": "OTC-DEMO-003",
            "first_name": "Emma",
            "last_name": "Clarke",
            "email": "emma.clarke@example.com",
            "phone": "07123 000003",
            "business_name": "Clarke Travel Studio",
            "status": "Awaiting Final Approval",
            "address": "8 Meadow View, Bristol",
            "postcode": "BS1 3CC",
        },
        "david": {
            "user": users["david"],
            "agent_id": "OTC-DEMO-004",
            "first_name": "David",
            "last_name": "Smith",
            "email": "david.smith@example.com",
            "phone": "07123 000004",
            "business_name": "David Smith Travel",
            "status": "Approved to Trade",
            "address": "19 Kings Road, Leeds",
            "postcode": "LS1 4DD",
        },
        "rachel": {
            "user": users["rachel"],
            "agent_id": "OTC-DEMO-005",
            "first_name": "Rachel",
            "last_name": "Brown",
            "email": "rachel.brown@example.com",
            "phone": "07123 000005",
            "business_name": "Rachel Brown Escapes",
            "status": "Suspended",
            "address": "31 Orchard Close, York",
            "postcode": "YO1 5EE",
        },
    }

    agents: dict[str, AgentProfile] = {}
    today = date.today()
    for key, spec in agent_specs.items():
        agent = db.scalar(select(AgentProfile).where(AgentProfile.user_id == spec["user"].id))
        if agent is None:
            agent = AgentProfile(
                user_id=spec["user"].id,
                organization_id=organization_id,
                agent_id=spec["agent_id"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                email=spec["email"],
            )
            db.add(agent)
            db.flush()

        agent.agent_id = spec["agent_id"]
        agent.organization_id = organization_id
        agent.first_name = spec["first_name"]
        agent.last_name = spec["last_name"]
        agent.email = spec["email"]
        agent.personal_email = spec["email"]
        agent.company_email = f"{spec['first_name'].lower()}.{spec['last_name'].lower()}@onetravelclub.co.uk"
        agent.portal_access_enabled = True
        agent.phone = spec["phone"]
        agent.business_name = spec["business_name"]
        agent.status = spec["status"]
        agent.joining_date = today - timedelta(days=30)
        agent.address = spec["address"]
        agent.postcode = spec["postcode"]
        agent.commission_bank_name = "Demo Bank"
        agent.commission_account_name = f"{spec['first_name']} {spec['last_name']}"
        agent.commission_sort_code = "00-00-00"
        agent.commission_account_number = "12345678"
        agents[key] = agent

    return agents


def ensure_demo_memberships_and_payments(db: Session, agents: dict[str, AgentProfile]) -> None:
    today = date.today()
    membership_specs = {
        "sarah": ("Starter Agent", "Active", "Paid", "Direct Debit", 0, None),
        "mark": ("Starter Agent", "Payment Pending", "Pending", None, 0, None),
        "emma": ("Professional Agent", "Active", "Paid", "Direct Debit", 0, None),
        "david": ("Professional Agent", "Active", "Paid", "Direct Debit", 0, None),
        "rachel": ("Professional Agent", "Suspended", "Failed", "Direct Debit", 2, today - timedelta(days=5)),
    }

    for key, (membership_type, membership_status, payment_status, payment_method, failed_count, suspension_date) in membership_specs.items():
        agent = agents[key]
        membership = db.scalar(select(Membership).where(Membership.agent_id == agent.id))
        if membership is None:
            membership = Membership(agent_id=agent.id)
            db.add(membership)
            db.flush()

        membership.membership_type = membership_type
        membership.setup_fee_amount = Decimal("299.00")
        membership.monthly_fee_amount = Decimal("49.00")
        membership.membership_status = membership_status
        membership.payment_status = payment_status
        membership.payment_method = payment_method
        membership.stripe_customer_id = f"cus_demo_{agent.agent_id.lower().replace('-', '_')}"
        membership.stripe_subscription_id = f"sub_demo_{agent.agent_id.lower().replace('-', '_')}" if payment_method else None
        membership.last_payment_date = today - timedelta(days=20) if payment_status == "Paid" else None
        membership.next_payment_date = today + timedelta(days=10) if payment_status == "Paid" else today - timedelta(days=2)
        membership.failed_payment_count = failed_count
        membership.access_level = "Demo access"
        membership.suspension_date = suspension_date
        membership.cancellation_date = None
        membership.internal_notes = f"Demo membership record for {agent.first_name}."

        if key == "mark":
            ensure_payment(
                db,
                agent,
                payment_type="Setup Fee",
                amount=Decimal("299.00"),
                status="Pending",
                due_date=today + timedelta(days=3),
                payment_date=None,
                notes="Demo seed: setup fee waiting for payment.",
            )
        elif key == "rachel":
            ensure_payment(
                db,
                agent,
                payment_type="Monthly Membership",
                amount=Decimal("49.00"),
                status="Failed",
                due_date=today - timedelta(days=5),
                payment_date=None,
                notes="Demo seed: failed monthly payment.",
            )
        else:
            ensure_payment(
                db,
                agent,
                payment_type="Setup Fee",
                amount=Decimal("299.00"),
                status="Paid",
                due_date=today - timedelta(days=25),
                payment_date=today - timedelta(days=24),
                notes="Demo seed: setup fee paid.",
            )
            ensure_payment(
                db,
                agent,
                payment_type="Monthly Membership",
                amount=Decimal("49.00"),
                status="Paid",
                due_date=today - timedelta(days=5),
                payment_date=today - timedelta(days=5),
                notes="Demo seed: monthly payment paid.",
            )


def ensure_payment(
    db: Session,
    agent: AgentProfile,
    *,
    payment_type: str,
    amount: Decimal,
    status: str,
    due_date: date,
    payment_date: date | None,
    notes: str,
) -> Payment:
    payment = db.scalar(
        select(Payment).where(
            Payment.agent_id == agent.id,
            Payment.payment_type == payment_type,
            Payment.notes == notes,
        )
    )
    if payment is None:
        payment = Payment(agent_id=agent.id, payment_type=payment_type, notes=notes, amount=amount)
        db.add(payment)
        db.flush()

    payment.amount = amount
    payment.currency = "GBP"
    payment.payment_status = status
    payment.due_date = due_date
    payment.payment_date = payment_date
    payment.stripe_payment_id = f"pi_demo_{agent.agent_id.lower().replace('-', '_')}_{payment_type.lower().replace(' ', '_')}"
    payment.invoice_url = f"https://example.com/demo-invoices/{agent.agent_id}-{payment_type.replace(' ', '-')}.pdf"
    return payment


def ensure_demo_documents(db: Session, agents: dict[str, AgentProfile], admin_user: User) -> None:
    today = date.today()
    verified_agents = ("emma", "david")
    for key, agent in agents.items():
        if key in verified_agents:
            ensure_document(db, agent, admin_user, "Contractor Agreement", "contractor-agreement.pdf", "Verified", True, True, today - timedelta(days=18))
            ensure_document(db, agent, admin_user, "ID Document", "passport.pdf", "Verified", False, True, today - timedelta(days=17))
            ensure_document(db, agent, admin_user, "Proof of Address", "proof-of-address.pdf", "Verified", False, True, today - timedelta(days=17))
        elif key == "sarah":
            ensure_document(db, agent, admin_user, "Contractor Agreement", "contractor-agreement.pdf", "Awaiting Review", True, False, None)
            ensure_document(db, agent, admin_user, "ID Document", "passport.pdf", "Awaiting Review", False, False, None)
        elif key == "mark":
            ensure_document(db, agent, admin_user, "ID Document", "passport.pdf", "Requested", False, False, None)
        elif key == "rachel":
            ensure_document(db, agent, admin_user, "Contractor Agreement", "contractor-agreement.pdf", "Verified", True, True, today - timedelta(days=45))
            ensure_document(db, agent, admin_user, "ID Document", "passport.pdf", "Verified", False, True, today - timedelta(days=45))
            ensure_document(db, agent, admin_user, "Proof of Address", "proof-of-address.pdf", "Rejected", False, False, None)


def ensure_document(
    db: Session,
    agent: AgentProfile,
    admin_user: User,
    document_type: str,
    file_name: str,
    status: str,
    signed: bool,
    verified: bool,
    review_date: date | None,
) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.agent_id == agent.id,
            Document.document_type == document_type,
            Document.file_name == file_name,
        )
    )
    if document is None:
        document = Document(
            agent_id=agent.id,
            document_type=document_type,
            file_name=file_name,
            file_url=f"https://example.com/demo-documents/{agent.agent_id}/{file_name}",
            uploaded_by=agent.user_id,
        )
        db.add(document)
        db.flush()

    document.status = status
    document.requires_signature = document_type == "Contractor Agreement"
    document.signed = signed
    document.signed_date = review_date if signed else None
    document.verified = verified
    document.verified_by = admin_user.id if verified else None
    document.verified_date = review_date if verified else None
    document.uploaded_date = review_date or date.today()
    document.notes = f"Demo {document_type.lower()} record."
    return document


def ensure_demo_onboarding(db: Session, agents: dict[str, AgentProfile], admin_user: User) -> None:
    all_step_titles = [step["title"] for step in DEFAULT_ONBOARDING_STEPS]
    complete_until_training = all_step_titles[:11]
    ready_titles = [title for title in all_step_titles if title != "Admin final approval"]

    set_agent_onboarding(db, agents["sarah"], complete_until_training[:9], admin_user, in_progress=["Attend compliance call", "Complete compliance training"])
    set_agent_onboarding(db, agents["mark"], ["Create account"], admin_user, in_progress=["Complete personal profile"])
    set_agent_onboarding(db, agents["emma"], ready_titles, admin_user, awaiting=["Admin final approval"])
    set_agent_onboarding(db, agents["david"], all_step_titles, admin_user)
    set_agent_onboarding(db, agents["rachel"], all_step_titles[:12], admin_user, rejected=["Set up recurring membership payment"])


def set_agent_onboarding(
    db: Session,
    agent: AgentProfile,
    completed: list[str],
    admin_user: User,
    *,
    in_progress: list[str] | None = None,
    awaiting: list[str] | None = None,
    rejected: list[str] | None = None,
) -> None:
    today = date.today()
    steps = list(db.scalars(select(OnboardingStep).order_by(OnboardingStep.sort_order)))
    completed_set = set(completed)
    in_progress_set = set(in_progress or [])
    awaiting_set = set(awaiting or [])
    rejected_set = set(rejected or [])

    for step in steps:
        progress = db.scalar(
            select(AgentOnboardingProgress).where(
                AgentOnboardingProgress.agent_id == agent.id,
                AgentOnboardingProgress.step_id == step.id,
            )
        )
        if progress is None:
            progress = AgentOnboardingProgress(agent_id=agent.id, step_id=step.id)
            db.add(progress)
            db.flush()

        if step.title in completed_set:
            progress.completion_status = "Complete"
            progress.completed_date = today - timedelta(days=5)
            progress.completed_by = admin_user.id
            progress.approved_by = admin_user.id if step.approval_required else None
            progress.approved_date = today - timedelta(days=5) if step.approval_required else None
        elif step.title in in_progress_set:
            progress.completion_status = "In Progress"
            progress.completed_date = None
            progress.completed_by = None
            progress.approved_by = None
            progress.approved_date = None
        elif step.title in awaiting_set:
            progress.completion_status = "Awaiting Review"
            progress.completed_date = None
            progress.completed_by = None
            progress.approved_by = None
            progress.approved_date = None
        elif step.title in rejected_set:
            progress.completion_status = "Rejected"
            progress.completed_date = None
            progress.completed_by = None
            progress.approved_by = None
            progress.approved_date = None
        else:
            progress.completion_status = "Not Started"
            progress.completed_date = None
            progress.completed_by = None
            progress.approved_by = None
            progress.approved_date = None

        progress.due_date = today + timedelta(days=14)
        progress.evidence_file_or_link = f"https://example.com/demo-evidence/{agent.agent_id}/{step.sort_order}"
        progress.admin_notes = f"Demo onboarding note for {step.title}."


def ensure_demo_training_progress(
    db: Session,
    agents: dict[str, AgentProfile],
    modules: dict[str, TrainingModule],
    training_user: User,
) -> None:
    mandatory_titles = [spec["title"] for spec in DEFAULT_MANDATORY_MODULES]

    for title in mandatory_titles[:5]:
        ensure_training_progress(db, agents["sarah"], modules[title], training_user, "Complete", passed=True, score=86)
    for title in mandatory_titles[5:8]:
        ensure_training_progress(db, agents["sarah"], modules[title], training_user, "In Progress")

    for title in mandatory_titles[:1]:
        ensure_training_progress(db, agents["mark"], modules[title], training_user, "In Progress")

    for title in mandatory_titles:
        ensure_training_progress(db, agents["emma"], modules[title], training_user, "Complete", passed=True, score=92)
        ensure_training_progress(db, agents["david"], modules[title], training_user, "Complete", passed=True, score=96)

    for title in mandatory_titles[:9]:
        ensure_training_progress(db, agents["rachel"], modules[title], training_user, "Complete", passed=True, score=82)
    ensure_training_progress(db, agents["rachel"], modules["Social Media & Advertising Policy"], training_user, "Failed", passed=False, score=55)

    further_modules = ("Closing Techniques", "Royal Caribbean Training", "Facebook Lead Generation")
    for title in further_modules:
        if title in modules:
            ensure_training_progress(db, agents["david"], modules[title], training_user, "Complete", passed=True, score=90)


def ensure_training_progress(
    db: Session,
    agent: AgentProfile,
    module: TrainingModule,
    training_user: User,
    status: str,
    *,
    passed: bool | None = None,
    score: int | None = None,
) -> AgentTrainingProgress:
    assignment = db.scalar(
        select(TrainingAssignment).where(
            TrainingAssignment.agent_id == agent.id,
            TrainingAssignment.training_module_id == module.id,
        )
    )
    if assignment is None:
        assignment = TrainingAssignment(
            agent_id=agent.id,
            training_module_id=module.id,
            assigned_by=training_user.id,
            mandatory=module.mandatory,
            due_date=date.today() + timedelta(days=14),
            notes="Demo training assignment.",
        )
        db.add(assignment)
        db.flush()

    progress = db.scalar(
        select(AgentTrainingProgress).where(
            AgentTrainingProgress.agent_id == agent.id,
            AgentTrainingProgress.training_module_id == module.id,
        )
    )
    if progress is None:
        progress = AgentTrainingProgress(
            assignment_id=assignment.id,
            agent_id=agent.id,
            training_module_id=module.id,
        )
        db.add(progress)
        db.flush()

    progress.assignment_id = assignment.id
    progress.progress_status = status
    progress.started_date = date.today() - timedelta(days=12)
    progress.completed_date = date.today() - timedelta(days=3) if status == "Complete" else None
    progress.score = score
    progress.passed = passed
    progress.certificate_issued = status == "Complete" and module.certificate_issued
    progress.expiry_date = date.today() + timedelta(days=365) if module.renewal_required and status == "Complete" else None
    progress.notes = f"Demo progress for {module.title}."
    return progress


def ensure_demo_policy_acceptances(
    db: Session,
    agents: dict[str, AgentProfile],
    policies: dict[str, CompliancePolicy],
    compliance_user: User,
) -> None:
    policy = policies.get("Advertising and Social Media")
    if policy is None:
        return

    for key in ("emma", "david"):
        acceptance = db.scalar(
            select(PolicyAcceptance).where(
                PolicyAcceptance.agent_id == agents[key].id,
                PolicyAcceptance.policy_id == policy.id,
            )
        )
        if acceptance is None:
            acceptance = PolicyAcceptance(
                agent_id=agents[key].id,
                policy_id=policy.id,
                accepted_by=agents[key].user_id,
                policy_version=policy.version,
                notes="Demo policy acceptance.",
            )
            db.add(acceptance)
            db.flush()
        acceptance.accepted_by = agents[key].user_id
        acceptance.policy_version = policy.version


def ensure_demo_live_sessions(db: Session) -> dict[str, LiveTrainingSession]:
    today = date.today()
    session_specs = {
        "welcome": ("Demo Welcome Call", "Welcome Call", today - timedelta(days=20), time(10, 0), time(11, 0), "Training Manager"),
        "compliance": ("Demo Compliance Call", "Compliance Call", today - timedelta(days=14), time(10, 0), time(11, 30), "Compliance Manager"),
        "systems": ("Demo CRM Systems Training", "Systems Training Call", today - timedelta(days=7), time(14, 0), time(15, 0), "Training Manager"),
        "final": ("Demo Final Sign-Off Call", "Final Sign-Off Call", today + timedelta(days=2), time(11, 0), time(11, 30), "Admin"),
    }
    sessions: dict[str, LiveTrainingSession] = {}
    for key, (title, session_type, session_date, start_time, end_time, host) in session_specs.items():
        session = db.scalar(select(LiveTrainingSession).where(LiveTrainingSession.title == title))
        if session is None:
            session = LiveTrainingSession(title=title, session_type=session_type, date=session_date)
            db.add(session)
            db.flush()

        session.session_type = session_type
        session.description = f"Demo {session_type.lower()} for onboarding agents."
        session.date = session_date
        session.start_time = start_time
        session.end_time = end_time
        session.trainer_host = host
        session.meeting_link = "https://example.com/demo-meeting"
        session.recording_link = "https://example.com/demo-recording"
        session.attendance_required = True
        session.follow_up_quiz_required = session_type == "Compliance Call"
        session.certificate_issued = False
        session.notes = "Demo live training session."
        sessions[key] = session
    return sessions


def ensure_demo_attendance(
    db: Session,
    agents: dict[str, AgentProfile],
    sessions: dict[str, LiveTrainingSession],
    training_user: User,
) -> None:
    ensure_attendance(db, sessions["welcome"], agents["sarah"], "Attended", training_user)
    ensure_attendance(db, sessions["compliance"], agents["sarah"], "Missed", training_user, follow_up_required=True)
    ensure_attendance(db, sessions["welcome"], agents["mark"], "Invited", training_user)
    ensure_attendance(db, sessions["welcome"], agents["emma"], "Attended", training_user)
    ensure_attendance(db, sessions["compliance"], agents["emma"], "Attended", training_user)
    ensure_attendance(db, sessions["welcome"], agents["david"], "Attended", training_user)
    ensure_attendance(db, sessions["compliance"], agents["david"], "Attended", training_user)
    ensure_attendance(db, sessions["systems"], agents["david"], "Attended", training_user)
    ensure_attendance(db, sessions["welcome"], agents["rachel"], "Attended", training_user)
    ensure_attendance(db, sessions["compliance"], agents["rachel"], "Watched Recording", training_user, watched_recording=True)


def ensure_attendance(
    db: Session,
    session: LiveTrainingSession,
    agent: AgentProfile,
    status: str,
    marked_by: User,
    *,
    follow_up_required: bool = False,
    watched_recording: bool = False,
) -> AttendanceLog:
    attendance = db.scalar(
        select(AttendanceLog).where(
            AttendanceLog.session_id == session.id,
            AttendanceLog.agent_id == agent.id,
        )
    )
    if attendance is None:
        attendance = AttendanceLog(session_id=session.id, agent_id=agent.id)
        db.add(attendance)
        db.flush()

    attendance.attendance_status = status
    attendance.join_time = session.start_time if status in ("Attended", "Late") else None
    attendance.leave_time = session.end_time if status in ("Attended", "Late") else None
    attendance.duration_attended = 60 if status in ("Attended", "Late") else None
    attendance.marked_by = marked_by.id
    attendance.marked_date = date.today()
    attendance.notes = "Demo attendance record."
    attendance.follow_up_required = follow_up_required
    attendance.watched_recording = watched_recording or status == "Watched Recording"
    attendance.recording_completed_date = date.today() if attendance.watched_recording else None
    return attendance


def ensure_demo_certificates(db: Session, agents: dict[str, AgentProfile], modules: dict[str, TrainingModule]) -> None:
    for key in ("emma", "david"):
        ensure_certificate(db, agents[key], modules["Compliance & Customer Money"], "Compliance Training Certificate", renewal_required=True)
        ensure_certificate(db, agents[key], modules["Data Protection & GDPR"], "GDPR Training Certificate", renewal_required=True)
        ensure_certificate(db, agents[key], modules["Final Assessment"], "Final Assessment Certificate", renewal_required=False)

    ensure_certificate(
        db,
        agents["rachel"],
        modules["Compliance & Customer Money"],
        "Compliance Training Certificate",
        renewal_required=True,
        status="Expired",
        expiry_date=date.today() - timedelta(days=10),
    )


def ensure_certificate(
    db: Session,
    agent: AgentProfile,
    module: TrainingModule,
    certificate_name: str,
    *,
    renewal_required: bool,
    status: str = "Active",
    expiry_date: date | None = None,
) -> Certificate:
    certificate = db.scalar(
        select(Certificate).where(
            Certificate.agent_id == agent.id,
            Certificate.training_module_id == module.id,
            Certificate.certificate_name == certificate_name,
        )
    )
    if certificate is None:
        certificate = Certificate(
            agent_id=agent.id,
            training_module_id=module.id,
            certificate_name=certificate_name,
            certificate_url=f"https://example.com/demo-certificates/{agent.agent_id}/{module.id}.pdf",
            issued_date=date.today() - timedelta(days=3),
        )
        db.add(certificate)
        db.flush()

    certificate.issued_date = date.today() - timedelta(days=3)
    certificate.expiry_date = expiry_date or (date.today() + timedelta(days=365) if renewal_required else None)
    certificate.renewal_required = renewal_required
    certificate.status = status
    return certificate


def ensure_demo_audit_logs(db: Session, agents: dict[str, AgentProfile], users: dict[str, User]) -> None:
    for key, agent in agents.items():
        ensure_audit_log(
            db,
            action_type="Account created",
            agent=agent,
            created_by=users["admin"],
            description=f"Demo audit: {agent.first_name} {agent.last_name} account created.",
            user_id=agent.user_id,
        )

    ensure_audit_log(db, "Payment status changed", agents["sarah"], users["admin"], "Demo audit: Sarah payment marked paid.", "Pending", "Paid")
    ensure_audit_log(db, "Document verified", agents["emma"], users["compliance"], "Demo audit: Emma ID and proof of address verified.")
    ensure_audit_log(db, "Training module completed", agents["emma"], users["training"], "Demo audit: Emma completed mandatory training.")
    ensure_audit_log(db, "Call attendance marked", agents["david"], users["training"], "Demo audit: David attended welcome and compliance calls.")
    ensure_audit_log(db, "Agent approved to trade", agents["david"], users["admin"], "Demo audit: David approved to trade.", "Awaiting Final Approval", "Approved to Trade")
    ensure_audit_log(db, "Agent suspended", agents["rachel"], users["admin"], "Demo audit: Rachel suspended after failed payment.", "Active Agent", "Suspended")


def ensure_audit_log(
    db: Session,
    action_type: str,
    agent: AgentProfile,
    created_by: User,
    description: str,
    previous_value: str | None = None,
    new_value: str | None = None,
    *,
    user_id: int | None = None,
) -> AuditLog:
    if action_type not in AUDIT_ACTION_TYPES:
        raise ValueError(f"Unsupported audit action type: {action_type}")

    audit_log = db.scalar(
        select(AuditLog).where(
            AuditLog.agent_id == agent.id,
            AuditLog.action_type == action_type,
            AuditLog.description == description,
        )
    )
    if audit_log is None:
        audit_log = AuditLog(
            agent_id=agent.id,
            user_id=user_id or agent.user_id,
            action_type=action_type,
            description=description,
            created_by=created_by.id,
            created_date=datetime.utcnow(),
        )
        db.add(audit_log)
        db.flush()

    audit_log.previous_value = previous_value
    audit_log.new_value = new_value
    audit_log.created_by = created_by.id
    return audit_log


if __name__ == "__main__":
    seed_demo_data()
