from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.audit import router as audit_router
from app.api.admin import router as admin_router
from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.certificates import router as certificates_router
from app.api.compliance import router as compliance_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.live_training import router as live_training_router
from app.api.messages import router as messages_router
from app.api.memberships import router as memberships_router
from app.api.notifications import router as notifications_router
from app.api.onboarding import router as onboarding_router
from app.api.organizations import router as organizations_router
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


@app.middleware("http")
async def reject_oversized_requests(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            request_size = int(content_length)
        except ValueError:
            request_size = 0
        if request_size > settings.max_upload_size_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Uploads must be {settings.max_upload_size_mb}MB or smaller. Please compress the file or use a hosted video embed."
                },
            )

    return await call_next(request)


settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploaded-files", StaticFiles(directory=settings.upload_dir), name="uploaded_files")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(audit_router)
app.include_router(memberships_router)
app.include_router(notifications_router)
app.include_router(onboarding_router)
app.include_router(organizations_router)
app.include_router(training_router)
app.include_router(live_training_router)
app.include_router(messages_router)
app.include_router(documents_router)
app.include_router(compliance_router)
app.include_router(certificates_router)
app.include_router(resources_router)
app.include_router(reports_router)
app.include_router(stripe_router)
app.include_router(health_router)
