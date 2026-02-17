"""Pydantic schemas for channel-related requests."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelConnectRequest(BaseModel):
    """Request payload for forwarding OAuth channel connection to MCP.
    
    Contains all necessary data for MCP to persist the channel connection.
    """
    
    user_id: UUID = Field(..., description="User's unique identifier")
    youtube_channel_id: str = Field(..., description="YouTube channel ID")
    channel_name: str = Field(..., description="YouTube channel display name")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")


class ChannelConnectResponse(BaseModel):
    """Response from MCP after channel connection."""
    
    success: bool
    channel_id: str
    channel_name: str
    message: Optional[str] = None
