"""Execute endpoint for message processing."""
import logging

from fastapi import APIRouter, HTTPException

from app.clients.mcp_client import MCPClient, MCPClientError
from app.schemas.request import ExecuteRequest
from app.schemas.response import ExecuteResponse, ErrorResponse


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["execute"])


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    status_code=200,
    summary="Execute Message",
    description="Process a user message and get a response from MCP",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "MCP server unavailable"},
    },
)
async def execute(request: ExecuteRequest) -> ExecuteResponse:
    """Process a message through the MCP server.

    Args:
        request: ExecuteRequest containing user_id, channel_id, and message.

    Returns:
        ExecuteResponse: Answer, confidence, and tools used.

    Raises:
        HTTPException: If request processing fails.
    """
    logger.info(
        f"Execute request received: user_id={request.user_id}, channel_id={request.channel_id}"
    )

    mcp_client = MCPClient()

    try:
        response = await mcp_client.execute(
            user_id=request.user_id,
            channel_id=request.channel_id,
            message=request.message,
            metadata=request.metadata,
        )

        return response

    except MCPClientError as e:
        logger.error(f"MCP execution failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.exception(f"Unexpected error during execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred",
        ) from e
