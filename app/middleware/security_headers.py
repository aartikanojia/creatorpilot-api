"""Security headers middleware for enhanced protection."""
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Adds standard security headers to protect against common attacks:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME sniffing
    - Content type attacks
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add security headers to response.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler.

        Returns:
            Response: The response with security headers.
        """
        response = await call_next(request)

        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (disable sensitive features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response
