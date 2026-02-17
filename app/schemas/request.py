"""Request schemas for API validation."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """Request model for /api/v1/execute endpoint.

    Attributes:
        user_id: Unique identifier for the user making the request.
        channel_id: Unique identifier for the channel/conversation.
        message: The user message to process.
        metadata: Optional metadata for the request.
    """

    user_id: str = Field(..., min_length=1, description="User identifier")
    channel_id: str = Field(..., min_length=1,
                            description="Channel identifier")
    message: str = Field(..., min_length=1, max_length=10000,
                         description="User message")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata for the request"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "channel_id": "660e8400-e29b-41d4-a716-446655440001",
                "message": "Show me my channel performance for last week",
                "metadata": {"user_plan": "PRO"}
            }
        }
