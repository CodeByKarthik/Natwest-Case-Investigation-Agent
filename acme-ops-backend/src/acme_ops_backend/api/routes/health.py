from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """
    Return API process health.

    This endpoint intentionally does not require authentication.
    """
    return {
        "status": "ok",
        "service": "natwest-ops-api",
    }
