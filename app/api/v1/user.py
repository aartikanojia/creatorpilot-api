"""User status endpoint for plan and usage info."""
import logging

import httpx
from fastapi import APIRouter

from app.config import get_settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["user"])


@router.get(
    "/user/status",
    summary="Get User Status",
    description="Returns user plan and current usage without incrementing",
)
async def get_user_status(user_id: str):
    """Proxy to MCP /api/v1/user/status endpoint.

    Args:
        user_id: User identifier.

    Returns:
        Dict with user_plan and usage.
    """
    settings = get_settings()
    mcp_url = f"{settings.mcp_base_url.rstrip('/')}/api/v1/user/status"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                mcp_url,
                params={"user_id": user_id},
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Failed to fetch user status from MCP: {e}")
        # Fail-open: return free with default usage
        return {
            "user_plan": "free",
            "usage": {
                "used": 0,
                "limit": 3,
                "exhausted": False,
            },
        }
