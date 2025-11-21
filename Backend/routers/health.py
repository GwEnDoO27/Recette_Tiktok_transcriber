from fastapi import APIRouter  # type: ignore

health = APIRouter()


# Route de santé pour vérifier le service
@health.get("/health", status_code=200)
async def health_check():
    """Route de vérification de santé du service"""
    return {
        "status": "healthy",
        "service": "Api de speech-to-text",
    }
