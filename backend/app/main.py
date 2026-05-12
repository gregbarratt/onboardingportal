from fastapi import FastAPI

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.live_training import router as live_training_router
from app.api.memberships import router as memberships_router
from app.api.onboarding import router as onboarding_router
from app.api.training import router as training_router


app = FastAPI(
    title="Travel Agent Onboarding Hub API",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(memberships_router)
app.include_router(onboarding_router)
app.include_router(training_router)
app.include_router(live_training_router)
app.include_router(documents_router)
app.include_router(health_router)
