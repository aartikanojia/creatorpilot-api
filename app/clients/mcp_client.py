"""Client for communicating with MCP server."""
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings
from app.schemas.response import ExecuteResponse

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""
    pass


class MCPClient:
    """HTTP client for MCP server communication."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.mcp_base_url.rstrip("/")
        self.timeout = settings.mcp_timeout

    async def execute(
        self,
        user_id: str,
        channel_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecuteResponse:
        """Forward execute request to MCP.

        Args:
            user_id: User identifier.
            channel_id: Channel identifier.
            message: User message to process.
            metadata: Optional metadata for the request.

        Returns:
            ExecuteResponse: Structured response from MCP.

        Raises:
            MCPClientError: If MCP request fails.
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "channel_id": channel_id,
            "message": message,
            "metadata": metadata if metadata is not None else {},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    f"Forwarding execute request to MCP: user_id={user_id}, channel_id={channel_id}"
                )

                response = await client.post(
                    f"{self.base_url}/execute",
                    json=payload,
                )
                response.raise_for_status()

                # Parse MCP response and transform to gateway format
                data = response.json()

                # Pass through PLAN_LIMIT_REACHED responses directly
                # so the frontend receives the usage metadata
                if not data.get("success", False):
                    error = data.get("error", {})
                    error_code = error.get("code", "") if isinstance(error, dict) else ""

                    if error_code == "PLAN_LIMIT_REACHED":
                        logger.info(f"Plan limit reached for user_id={user_id}")
                        return ExecuteResponse(
                            answer=error.get("message", "Plan limit reached"),
                            confidence=0.0,
                            tools_used=[],
                            metadata=data.get("metadata"),
                            success=False,
                            error=error,
                        )

                    raise MCPClientError(
                        f"MCP execution failed: {data.get('error', 'Unknown error')}")

                # Transform MCP response to gateway response format
                result = ExecuteResponse(
                    answer=data.get("content") or "",
                    confidence=data.get("metadata", {}).get("confidence", 0.0),
                    tools_used=data.get("tools_used", []),
                    content_type=data.get("content_type"),
                    tool_outputs=data.get("tool_outputs"),
                    metadata=data.get("metadata"),
                )

                logger.info(
                    f"MCP execute succeeded: user_id={user_id}, confidence={result.confidence}"
                )

                return result

        except httpx.TimeoutException as e:
            logger.error(f"MCP request timeout: {str(e)}")
            raise MCPClientError(
                f"MCP server request timed out after {self.timeout} seconds"
            ) from e

        except httpx.HTTPError as exc:
            logger.error("MCP execute request failed: %s", exc)
            raise MCPClientError(
                f"MCP server request failed: {str(exc)}") from exc

    async def ping(self) -> bool:
        """
        Lightweight MCP reachability check.

        Uses /execute with a harmless ping payload instead of relying
        on a dedicated /health endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.post(
                    f"{self.base_url}/execute",
                    json={
                        "user_id": "health_check",
                        "channel_id": "health_check",
                        "message": "ping",
                    },
                )
                return response.status_code == 200
        except Exception:
            return False
