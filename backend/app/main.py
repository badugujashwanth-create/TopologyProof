"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the configured TopologyProof API application."""
    resolved = settings or get_settings()
    application = FastAPI(title=resolved.app_name, version=resolved.app_version)
    application.state.settings = resolved
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")
    return application
