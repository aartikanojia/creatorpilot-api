"""YouTube OAuth endpoints for connecting user's YouTube channel.

Supports two flows:
1. API flow: /start returns JSON with auth_url (for API clients)
2. Mobile flow: /login redirects to Google, /callback redirects to deep link
"""
import logging
import secrets
import uuid
from typing import Optional
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.channel import ChannelConnectRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/youtube", tags=["youtube-auth"])

# ── In-memory state store for CSRF protection ────────────────────────────
# Maps state_token → user_id. Entries are consumed on callback.
_pending_states: dict[str, str] = {}

# Deep link scheme for mobile app callback
MOBILE_DEEP_LINK = "creatorpilot://auth/callback"


class AuthUrlResponse(BaseModel):
    """Response model for /auth/youtube/start endpoint."""

    auth_url: str


class CallbackResponse(BaseModel):
    """Response model for /auth/youtube/callback endpoint."""

    success: bool
    channel_id: str
    channel_name: str


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


def _build_google_auth_url(user_id: str, settings) -> str:
    """Build Google OAuth authorization URL with state security.

    Generates a CSRF state token, stores it, and builds the full
    Google OAuth consent URL.

    Args:
        user_id: Validated user UUID string.
        settings: Application settings.

    Returns:
        Full Google OAuth authorization URL.
    """
    # Generate CSRF state token and combine with user_id
    state_token = secrets.token_urlsafe(16)
    state_value = f"{user_id}:{state_token}"

    # Store for validation on callback
    _pending_states[state_token] = user_id

    # Parse scopes from comma-separated string
    scopes = [s.strip() for s in settings.youtube_scopes.split(",")]
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state_value,
    }

    return f"{settings.google_auth_url}?{urlencode(params)}"


def _validate_state(state: str) -> uuid.UUID:
    """Validate and consume the state parameter from callback.

    Args:
        state: State parameter in format "user_id:state_token".

    Returns:
        Validated user UUID.

    Raises:
        ValueError: If state is invalid or token doesn't match.
    """
    if ":" not in state:
        # Legacy format: state is just user_id (backward compat)
        return uuid.UUID(state)

    parts = state.split(":", 1)
    user_id_str, state_token = parts[0], parts[1]

    # Validate user_id format
    user_uuid = uuid.UUID(user_id_str)

    # Validate state token exists and matches
    stored_user_id = _pending_states.pop(state_token, None)
    if stored_user_id is None:
        raise ValueError(f"Unknown or expired state token")
    if stored_user_id != user_id_str:
        raise ValueError(f"State token user_id mismatch")

    return user_uuid


# ── /start — API flow (returns JSON) ─────────────────────────────────────

@router.get(
    "/start",
    response_model=AuthUrlResponse,
    summary="Start YouTube OAuth (API)",
    description="Generate Google OAuth authorization URL for YouTube connection. Returns JSON.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def youtube_auth_start(
    user_id: str = Query(..., description="User ID initiating the OAuth flow"),
) -> AuthUrlResponse:
    """Generate Google OAuth authorization URL (returns JSON).

    Args:
        user_id: The user's unique identifier.

    Returns:
        AuthUrlResponse: Contains the Google OAuth URL.
    """
    settings = get_settings()

    if not settings.google_client_id:
        logger.error("GOOGLE_CLIENT_ID not configured")
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    if not settings.google_redirect_uri:
        logger.error("GOOGLE_REDIRECT_URI not configured")
        raise HTTPException(status_code=500, detail="Google OAuth redirect URI is not configured")

    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format. Expected UUID.")

    auth_url = _build_google_auth_url(user_id, settings)
    logger.info(f"Generated OAuth URL for user_id={user_id}")

    return AuthUrlResponse(auth_url=auth_url)


# ── /login — Mobile flow (redirects to Google) ───────────────────────────

@router.get(
    "/login",
    summary="Start YouTube OAuth (Mobile)",
    description="Redirects directly to Google OAuth consent screen. Use from mobile browser.",
    responses={302: {"description": "Redirect to Google OAuth"}},
)
async def youtube_auth_login(
    user_id: str = Query(
        default="00000000-0000-0000-0000-000000000001",
        description="User ID initiating the OAuth flow",
    ),
):
    """Redirect to Google OAuth consent screen.

    Mobile-friendly: opens this URL in system browser and it redirects
    directly to Google. No JSON parsing needed on the client side.

    Args:
        user_id: The user's unique identifier.
    """
    settings = get_settings()

    if not settings.google_client_id:
        logger.error("GOOGLE_CLIENT_ID not configured")
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    if not settings.google_redirect_uri:
        logger.error("GOOGLE_REDIRECT_URI not configured")
        raise HTTPException(status_code=500, detail="Google OAuth redirect URI is not configured")

    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format. Expected UUID.")

    auth_url = _build_google_auth_url(user_id, settings)
    logger.info(f"Redirecting to Google OAuth for user_id={user_id}")

    return RedirectResponse(url=auth_url, status_code=302)


# ── /callback — Handles Google redirect, redirects to deep link ──────────

@router.get(
    "/callback",
    summary="YouTube OAuth Callback",
    description="Handle Google OAuth callback. Redirects to mobile deep link.",
    responses={302: {"description": "Redirect to mobile deep link"}},
)
async def youtube_auth_callback(
    code: str = Query(..., description="OAuth authorization code from Google"),
    state: str = Query(..., description="State parameter containing user_id:token"),
):
    """Handle Google OAuth callback.

    Exchanges authorization code for tokens, fetches YouTube channel info,
    forwards channel connection to MCP, then redirects to mobile deep link.

    On success: creatorpilot://auth/callback?status=success&user_id=...&channel_id=...&channel_name=...
    On failure: creatorpilot://auth/callback?status=error&detail=...
    """
    settings = get_settings()

    # Validate state parameter (CSRF protection)
    try:
        user_uuid = _validate_state(state)
    except ValueError as e:
        logger.error(f"Invalid state parameter: {state} — {e}")
        return RedirectResponse(
            url=f"{MOBILE_DEEP_LINK}?status=error&detail={quote(str(e))}",
            status_code=302,
        )

    # Exchange code for tokens
    try:
        tokens = await _exchange_code_for_tokens(code, settings)
    except Exception as e:
        logger.error(f"Token exchange failed: {str(e)}")
        return RedirectResponse(
            url=f"{MOBILE_DEEP_LINK}?status=error&detail={quote('Token exchange failed')}",
            status_code=302,
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        logger.error("No access_token in token response")
        return RedirectResponse(
            url=f"{MOBILE_DEEP_LINK}?status=error&detail={quote('No access token received')}",
            status_code=302,
        )

    # Fetch YouTube channel info
    try:
        channel_info = await _fetch_youtube_channel(access_token, settings)
    except Exception as e:
        logger.error(f"YouTube API call failed: {str(e)}")
        return RedirectResponse(
            url=f"{MOBILE_DEEP_LINK}?status=error&detail={quote('Failed to fetch channel info')}",
            status_code=302,
        )

    youtube_channel_id = channel_info["id"]
    channel_name = channel_info["title"]

    # Forward channel connection to MCP for persistence
    try:
        await _forward_channel_to_mcp(
            settings=settings,
            user_id=user_uuid,
            youtube_channel_id=youtube_channel_id,
            channel_name=channel_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception as e:
        logger.error(f"MCP forwarding failed: {str(e)}")
        return RedirectResponse(
            url=f"{MOBILE_DEEP_LINK}?status=error&detail={quote('Failed to save connection')}",
            status_code=302,
        )

    logger.info(
        f"Successfully connected YouTube channel: "
        f"user_id={user_uuid}, channel={channel_name}"
    )

    # Redirect to mobile deep link with channel info
    params = urlencode({
        "status": "success",
        "user_id": str(user_uuid),
        "channel_id": youtube_channel_id,
        "channel_name": channel_name,
    })
    return RedirectResponse(
        url=f"{MOBILE_DEEP_LINK}?{params}",
        status_code=302,
    )


async def _exchange_code_for_tokens(code: str, settings) -> dict:
    """Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from Google OAuth.
        settings: Application settings.

    Returns:
        dict: Token response from Google.

    Raises:
        Exception: If token exchange fails.
    """
    async with httpx.AsyncClient() as client:
        logger.info(f"Exchanging code for tokens with redirect_uri={settings.google_redirect_uri}")
        response = await client.post(
            settings.google_token_url,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            error_body = response.text
            # Sanitize error body to avoid logging sensitive data
            sanitized_body = error_body[:200] + "..." if len(error_body) > 200 else error_body
            logger.error(f"Token exchange failed. Status: {response.status_code}")
            try:
                error_json = response.json()
                error_detail = error_json.get("error_description", error_json.get("error", "Unknown error"))
            except Exception:
                error_detail = "Token exchange failed"
            raise Exception(f"Token exchange failed: {error_detail}")

        return response.json()


async def _fetch_youtube_channel(access_token: str, settings) -> dict:
    """Fetch YouTube channel information using the access token.

    Args:
        access_token: Valid Google OAuth access token.
        settings: Application settings.

    Returns:
        dict: Channel info with 'id' and 'title'.

    Raises:
        Exception: If API call fails or no channel found.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            settings.youtube_channels_api,
            params={
                "part": "snippet,statistics",
                "mine": "true",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            error_detail = response.json().get("error", {}).get("message", response.text)
            raise Exception(f"YouTube API error: {error_detail}")

        data = response.json()
        items = data.get("items", [])

        if not items:
            raise Exception("No YouTube channel found for this account")

        channel = items[0]
        return {
            "id": channel["id"],
            "title": channel["snippet"]["title"],
        }


async def _forward_channel_to_mcp(
    settings,
    user_id: uuid.UUID,
    youtube_channel_id: str,
    channel_name: str,
    access_token: str,
    refresh_token: Optional[str],
) -> None:
    """Forward channel connection to MCP for persistence.

    Args:
        settings: Application settings.
        user_id: User's UUID.
        youtube_channel_id: YouTube channel ID.
        channel_name: Channel display name.
        access_token: OAuth access token.
        refresh_token: OAuth refresh token (may be None).

    Raises:
        Exception: If MCP request fails.
    """
    mcp_url = f"{settings.mcp_base_url}/channels/connect"
    
    request_data = ChannelConnectRequest(
        user_id=user_id,
        youtube_channel_id=youtube_channel_id,
        channel_name=channel_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
        logger.info(f"Forwarding channel connection to MCP: {mcp_url}")
        response = await client.post(
            mcp_url,
            json=request_data.model_dump(mode="json"),
            headers={"Content-Type": "application/json"},
        )

        if response.status_code not in (200, 201):
            # Don't log full response body as it may contain sensitive data
            logger.error(f"MCP channel connect failed. Status: {response.status_code}")
            raise Exception(f"MCP channel connect failed with status {response.status_code}")

        logger.info(f"Channel forwarded to MCP successfully for user_id={user_id}")


# ── /mobile/exchange — Native mobile OAuth code exchange ─────────────────

# iOS client ID from Google Cloud Console (public client — no secret)
IOS_CLIENT_ID = "697429001294-2mrf5v637ash0uj522spsoill1r9oqpq.apps.googleusercontent.com"
IOS_REDIRECT_URI = "com.googleusercontent.apps.697429001294-2mrf5v637ash0uj522spsoill1r9oqpq:/oauthredirect"

# Default user ID for Phase 1 (single-user mode)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


class MobileExchangeRequest(BaseModel):
    """Request body for mobile OAuth code exchange."""

    code: str
    code_verifier: Optional[str] = None
    user_id: str = DEFAULT_USER_ID


class MobileExchangeResponse(BaseModel):
    """Response from mobile OAuth code exchange."""

    success: bool
    user_id: str
    channel_id: str
    channel_name: str


@router.post(
    "/mobile/exchange",
    response_model=MobileExchangeResponse,
    summary="Exchange Mobile OAuth Code",
    description="Receive authorization code from flutter_appauth, exchange for tokens, connect channel.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid code or exchange failed"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def mobile_exchange(body: MobileExchangeRequest):
    """Exchange authorization code from native mobile OAuth.

    Called by Flutter after flutter_appauth obtains an authorization code.
    Exchanges code for tokens using the iOS public client (no secret),
    fetches YouTube channel info, and stores via MCP.

    Args:
        body: Contains authorization code and optional user_id.

    Returns:
        MobileExchangeResponse with channel connection details.
    """
    settings = get_settings()

    # Validate user_id
    try:
        user_uuid = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Exchange code for tokens (iOS public client — no secret needed)
    try:
        tokens = await _exchange_mobile_code_for_tokens(body.code, settings, body.code_verifier)
    except Exception as e:
        logger.error(f"Mobile token exchange failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {str(e)}",
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        logger.error("No access_token in mobile token response")
        raise HTTPException(
            status_code=500,
            detail="Google did not return an access token",
        )

    # Fetch YouTube channel info
    try:
        channel_info = await _fetch_youtube_channel(access_token, settings)
    except Exception as e:
        logger.error(f"YouTube API call failed (mobile): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch YouTube channel: {str(e)}",
        )

    youtube_channel_id = channel_info["id"]
    channel_name = channel_info["title"]

    # Forward to MCP for persistence
    try:
        await _forward_channel_to_mcp(
            settings=settings,
            user_id=user_uuid,
            youtube_channel_id=youtube_channel_id,
            channel_name=channel_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception as e:
        logger.error(f"MCP forwarding failed (mobile): {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save channel connection",
        )

    logger.info(
        f"Mobile OAuth success: user_id={user_uuid}, channel={channel_name}"
    )

    return MobileExchangeResponse(
        success=True,
        user_id=str(user_uuid),
        channel_id=youtube_channel_id,
        channel_name=channel_name,
    )


async def _exchange_mobile_code_for_tokens(
    code: str, settings, code_verifier: Optional[str] = None
) -> dict:
    """Exchange authorization code from native mobile OAuth.

    Uses the iOS public client (no client_secret required).
    The redirect_uri must match what flutter_appauth used.

    Args:
        code: Authorization code from flutter_appauth.
        settings: Application settings.

    Returns:
        dict: Token response from Google.
    """
    async with httpx.AsyncClient() as client:
        logger.info("Exchanging mobile auth code for tokens (iOS public client)")
        data = {
            "code": code,
            "client_id": IOS_CLIENT_ID,
            "redirect_uri": IOS_REDIRECT_URI,
            "grant_type": "authorization_code",
            **(({"code_verifier": code_verifier} if code_verifier else {})),
        }

        response = await client.post(
            settings.google_token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"Mobile token exchange failed. Status: {response.status_code}")
            try:
                error_json = response.json()
                error_detail = error_json.get(
                    "error_description",
                    error_json.get("error", "Unknown error"),
                )
            except Exception:
                error_detail = "Token exchange failed"
            raise Exception(error_detail)

        return response.json()
