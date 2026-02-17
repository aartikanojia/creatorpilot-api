"""Channel stats endpoint - proxies to MCP for real YouTube data."""
import logging

from fastapi import APIRouter, HTTPException, Query
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/channel", tags=["channel"])

TEMP_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.get(
    "/stats",
    summary="Get YouTube Channel Stats",
    description="Proxy to MCP to fetch real YouTube channel statistics for dashboard",
)
async def get_channel_stats(
    user_id: str = Query(default=TEMP_USER_ID, description="User ID"),
    period: str = Query(default="7d", description="Time period: 7d, 30d, or 6m"),
) -> dict:
    """Fetch channel stats from MCP server.

    Args:
        user_id: User's UUID.
        period: Time period for chart data.

    Returns:
        Channel statistics (subscriberCount, viewCount, videoCount, avgWatchTimeMinutes, dailyViews).

    Raises:
        HTTPException: If MCP request fails.
    """
    settings = get_settings()
    mcp_url = f"{settings.mcp_base_url.rstrip('/')}/channels/{user_id}/stats"

    try:
        async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
            response = await client.get(mcp_url, params={"period": period})

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="No connected YouTube channel found",
                )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"MCP channel stats error: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Failed to fetch channel stats",
        )
    except httpx.RequestError as e:
        logger.error(f"MCP channel stats request failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not reach analytics service",
        )


@router.get(
    "/top-video",
    summary="Get Most Watched Video",
    description="Proxy to MCP to fetch the top-performing video for the period",
)
async def get_top_video(
    user_id: str = Query(default=TEMP_USER_ID, description="User ID"),
    period: str = Query(default="7d", description="Time period: 7d, 30d, or 6m"),
) -> dict:
    """Fetch top video from MCP server.

    Args:
        user_id: User's UUID.
        period: Time period.

    Returns:
        Top video data (video_id, title, thumbnail_url, views, growth_percentage).
    """
    settings = get_settings()
    mcp_url = f"{settings.mcp_base_url.rstrip('/')}/analytics/top-video"

    try:
        async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
            response = await client.get(
                mcp_url,
                params={"user_id": user_id, "period": period},
            )
            response.raise_for_status()
            return response.json()

    except httpx.RequestError as e:
        logger.error(f"MCP top-video request failed: {e}")
        # Fail-open: return empty state
        return {
            "video_id": None,
            "title": None,
            "thumbnail_url": None,
            "views": 0,
            "growth_percentage": 0,
        }

