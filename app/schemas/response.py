"""Response schemas for API responses."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecuteResponse(BaseModel):
    """Response model for /api/v1/execute endpoint.

    Attributes:
        answer: The answer/response from the MCP server.
        confidence: Confidence score of the response (0-1).
        tools_used: List of tools/functions that were invoked.
        content_type: Type of content returned (e.g., analytics, text).
        tool_outputs: Outputs from each tool execution.
        metadata: Additional metadata from MCP response.
    """

    answer: str = Field("", description="Answer from the MCP server")
    confidence: float = Field(0.0, ge=0, le=1,
                              description="Confidence score (0-1)")
    tools_used: List[str] = Field(
        default_factory=list, description="Tools invoked")
    content_type: Optional[str] = Field(
        default=None, description="Type of content (e.g., analytics, text)")
    tool_outputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Outputs from tool executions")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata from MCP")
    success: Optional[bool] = Field(
        default=True, description="Whether execution succeeded")
    error: Optional[Dict[str, Any]] = Field(
        default=None, description="Error details (e.g., PLAN_LIMIT_REACHED)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "answer": "Here's your channel performance data.",
                "confidence": 0.67,
                "tools_used": ["fetch_analytics", "compute_metrics", "generate_chart"],
                "content_type": "analytics",
                "tool_outputs": {
                    "data": {"views": 15420, "subscribers": 1250},
                    "charts": {"chart_type": "line", "labels": ["Mon", "Tue"]}
                },
                "metadata": {"intent": "analytics", "user_plan": "PRO"}
            }
        }


class HealthResponse(BaseModel):
    """Response model for /health endpoint.

    Attributes:
        status: Health status of the service.
        version: API version.
        llm_provider: LLM provider configured in MCP (metadata only).
        dependencies: Status of external dependencies.
    """

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    llm_provider: str = Field(..., description="LLM provider configured in MCP")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Dependency health status")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "llm_provider": "gemini-flash-latest",
                "dependencies": {
                    "mcp": "ok"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model.

    Attributes:
        error: Error message.
        detail: Detailed error information.
    """

    error: str = Field(..., description="Error type")
    detail: Optional[str] = Field(None, description="Error details")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "error": "MCP_CLIENT_ERROR",
                "detail": "Failed to connect to MCP server",
            }
        }
