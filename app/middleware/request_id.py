"""Request ID middleware for request tracking."""
import logging
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request IDs to all requests and responses.

    This middleware generates a unique request ID for each incoming request
    and adds it to the response headers for request tracking.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add request ID.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler.

        Returns:
            Response: The response with request ID header.
        """
        # Get or generate request ID
        request_id = request.headers.get(
            REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Log the request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path}",
            extra={"request_id": request_id},
        )

        # Process the request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[REQUEST_ID_HEADER] = request_id

        return response
