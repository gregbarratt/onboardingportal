from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit import router as audit_router
from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.certificates import router as certificates_router
from app.api.compliance import router as compliance_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.live_training import router as live_training_router
from app.api.memberships import router as memberships_router
from app.api.notifications import router as notifications_router
from app.api.onboarding import router as onboarding_router
from app.api.reports import router as reports_router
from app.api.resources import router as resources_router
from app.api.training import router as training_router
from app.api.stripe import router as stripe_router
from app.core.config import settings


app = FastAPI(
    title="Travel Agent Onboarding Hub API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(audit_router)
app.include_router(memberships_router)
app.include_router(notifications_router)
app.include_router(onboarding_router)
app.include_router(training_router)
app.include_router(live_training_router)
app.include_router(documents_router)
app.include_router(compliance_router)
app.include_router(certificates_router)
app.include_router(resources_router)
app.include_router(reports_router)
app.include_router(stripe_router)
app.include_router(health_router)
