"""
Application FastAPI
"""

import os

from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from routers.health import health  # type: ignore
from routers.recipes import transform_tiktok  # type: ignore

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Configuration CORS depuis variables d'environnement
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
).split(",")

APP_CONFIG = {
    "title": os.getenv("APP_CONFIG_TITLE"),
    "description": os.getenv("APP_CONFIG_DESCRITPION"),
    "version": os.getenv("APP_CONFIG_VERSION"),
    "docs_url": "/docs",
    "openapi_url": "/openapi.json",
}

CORS_CONFIG = {
    "allow_origins": ALLOWED_ORIGINS,
    "allow_credentials": True,
    "allow_methods": os.getenv("CORS_ALLOW_METHODS"),
    "allow_headers": ["*"],
}

ROUTER_CONFIG = [
    {
        "router": transform_tiktok,
        "prefix": "/api",
        "tags": ["Convertion d'audio à text"],
    },
    {"router": health, "prefix": "/api", "tags": ["Health Check"]},
]

# ═══════════════════════════════════════════════════════════════════
# INITIALISATION DE L'APPLICATION
# ═══════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """
    Factory function pour créer et configurer l'application FastAPI.

    Returns:
        Application FastAPI configurée
    """
    # Créer l'application
    app = FastAPI(**APP_CONFIG)

    # Ajouter les middlewares
    _setup_middleware(app)

    # Ajouter les routers
    _setup_routers(app)

    # Ajouter les routes racine
    _setup_root_routes(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Configure les middlewares de l'application."""
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)


def _setup_routers(app: FastAPI) -> None:
    """Configure les routers de l'application."""
    for config in ROUTER_CONFIG:
        app.include_router(
            config["router"], prefix=config["prefix"], tags=config["tags"]
        )


def _setup_root_routes(app: FastAPI) -> None:
    """Configure les routes racine."""

    @app.get("/", tags=["Root"])
    async def root():
        """Endpoint racine de l'API."""
        return {
            "message": "Api Speech to text",
            "version": APP_CONFIG["version"],
            "status": "✅ Opérationnel",
        }


# Créer l'instance de l'application
app = create_app()
