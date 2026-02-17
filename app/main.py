"""FastAPI application entry point."""
import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import execute, health, channel, feedback, user
from app.api.v1.auth import youtube as youtube_auth
from app.config import get_settings
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API Gateway for Model Context Protocol (MCP) Server",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Parse CORS origins from config (comma-separated)
    cors_origins = [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]

    # Add CORS middleware with explicit origins
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    # Include routers
    app.include_router(health.router)
    app.include_router(execute.router)
    app.include_router(youtube_auth.router)
    app.include_router(channel.router)
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
    app.include_router(user.router)

    # Root endpoint
    @app.get("/", tags=["info"])
    async def root():
        """Root endpoint returning API info."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/docs" if settings.debug else "Not available",
        }

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Run on application startup."""
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"MCP Base URL: {settings.mcp_base_url}")

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown."""
        logger.info(f"Shutting down {settings.app_name}")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
