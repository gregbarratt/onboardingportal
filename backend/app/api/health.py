from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Travel Agent Onboarding Hub backend is running",
    }

