"""Health check endpoint."""
import logging

from fastapi import APIRouter

from app.clients.mcp_client import MCPClient
from app.config import get_settings
from app.schemas.response import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Health Check",
    description="Check API health and report dependency status",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    - API is considered healthy if it can accept traffic.
    - Dependencies (like MCP) are reported as ok/degraded.
    - This seen as production-safe behavior for orchestrators.
    """
    settings = get_settings()
    mcp_client = MCPClient()

    dependencies: dict[str, str] = {
        "mcp": "unknown"
    }

    try:
        is_mcp_reachable = await mcp_client.ping()
        dependencies["mcp"] = "ok" if is_mcp_reachable else "degraded"
    except Exception as exc:
        logger.warning("MCP dependency degraded: %s", exc)
        dependencies["mcp"] = "degraded"

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        dependencies=dependencies,
    )
