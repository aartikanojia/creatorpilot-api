# CreatorPilot API

Production-grade FastAPI service that acts as an API gateway for an internal Model Context Protocol (MCP) server.

## Overview

**CreatorPilot API** is a clean, minimal HTTP API gateway that:

- Exposes a stable API for frontend clients
- Forwards requests to the MCP server
- Hides MCP internals
- Acts as the product boundary
- **Supports YouTube OAuth** for connecting user YouTube channels

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **Pydantic v2** - Data validation and settings management
- **httpx** - Async HTTP client for MCP communication
- **Uvicorn** - ASGI application server

## Project Structure

```
creatorpilot-api/
├── app/
│   ├── main.py              # FastAPI application factory
│   ├── config.py            # Configuration & settings
│   ├── api/
│   │   └── v1/
│   │       ├── health.py      # Health check endpoint
│   │       ├── execute.py     # Message execution endpoint
│   │       ├── channel.py     # Channel stats & top video proxy
│   │       ├── feedback.py    # User feedback endpoint
│   │       ├── user.py        # User status endpoint
│   │       └── auth/
│   │           ├── __init__.py
│   │           └── youtube.py # YouTube OAuth endpoints
│   ├── clients/
│   │   └── mcp_client.py    # MCP HTTP client (with plan-limit handling)
│   ├── schemas/
│   │   ├── request.py       # Request models
│   │   ├── response.py      # Response models (success/error fields)
│   │   └── channel.py       # Channel DTOs for MCP forwarding
│   └── middleware/
│       ├── request_id.py        # Request ID tracking
│       └── security_headers.py  # Security headers middleware
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

> **Note**: Channel persistence is handled by MCP (creatorpilot-mcp). The API only handles OAuth orchestration and forwards channel data to MCP via HTTP.

## Endpoints

### Health Check

```http
GET /health
```

Returns service health status and version.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Execute Message

```http
POST /api/v1/execute
Content-Type: application/json

{
  "user_id": "user_123",
  "channel_id": "channel_456",
  "message": "What is the weather today?"
}
```

Forwards the user message to the MCP server for processing.

**Response (200 OK):**

```json
{
  "answer": "The weather is sunny with 72°F temperature.",
  "confidence": 0.95,
  "tools_used": ["weather_tool"]
}
```

**Error Response (503 Service Unavailable):**

```json
{
  "error": "MCP_CLIENT_ERROR",
  "detail": "MCP server request failed"
}
```

**Plan Limit Response (200 OK, `success: false`):**

When a user exceeds their plan's message limit, the API returns a structured error so the frontend can display upgrade prompts:

```json
{
  "answer": "Plan limit reached",
  "confidence": 0.0,
  "tools_used": [],
  "success": false,
  "error": {
    "code": "PLAN_LIMIT_REACHED",
    "message": "You have used all your free messages"
  },
  "metadata": { "usage": { "used": 3, "limit": 3 } }
}
```

### Channel Stats

```http
GET /api/v1/channel/stats?user_id=<user_id>&period=7d
```

Proxies to MCP to fetch real YouTube channel statistics (subscribers, views, video count, daily views chart data).

**Query Parameters:** `period` — `7d` (default), `30d`, or `6m`.

### Top Video

```http
GET /api/v1/channel/top-video?user_id=<user_id>&period=7d
```

Returns the top-performing video for the given period. Fails open with empty data if MCP is unreachable.

### User Status

```http
GET /api/v1/user/status?user_id=<user_id>
```

Returns the user's plan and current usage. Fails open with free-tier defaults.

**Response (200 OK):**

```json
{
  "user_plan": "free",
  "usage": { "used": 1, "limit": 3, "exhausted": false }
}
```

### Feedback

```http
POST /api/v1/feedback/
Content-Type: application/json

{ "message_id": "msg_123", "feedback": "positive" }
```

Submits user feedback (`positive` or `negative`) for a message. Currently logged; database persistence planned.

### YouTube OAuth - Start

```http
GET /api/v1/auth/youtube/start?user_id=<user_uuid>
```

Generates a Google OAuth authorization URL for connecting a YouTube channel.

**Response (200 OK):**

```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### YouTube OAuth - Callback

```http
GET /api/v1/auth/youtube/callback?code=<auth_code>&state=<user_id>
```

Handles the OAuth callback from Google. Exchanges the authorization code for tokens, fetches YouTube channel information, and forwards the connection to MCP for persistence.

**Response (200 OK):**

```json
{
  "success": true,
  "channel_id": "UC...",
  "channel_name": "My YouTube Channel"
}
```

**Error Response (400 Bad Request):**

```json
{
  "error": "OAUTH_ERROR",
  "detail": "Failed to exchange authorization code"
}

## Installation

### Prerequisites

- Python 3.11 or higher
- pip or poetry for package management

### Local Setup

1. **Clone the repository:**

   ```bash
   cd /Users/mohitkumar/Documents/createrai/creatorpilot-api
   ```

2. **Create a virtual environment:**

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Configure Google OAuth (for YouTube integration):**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials (Web application)
   - Add authorized redirect URI (e.g., `http://localhost:3000/auth/youtube/callback`)
   - Copy Client ID and Client Secret to your `.env` file

## Running the Application

### Development Mode (with auto-reload)

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Production Mode

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker

### Build

```bash
docker build -t creatorpilot-api:latest .
```

### Run

```bash
docker run -p 8000:8000 \
  -e MCP_BASE_URL=http://mcp-server:8001 \
  -e ENVIRONMENT=production \
  creatorpilot-api:latest
```

## Environment Variables

| Variable               | Default                                      | Description                              |
| ---------------------- | -------------------------------------------- | ---------------------------------------- |
| `ENVIRONMENT`          | `development`                                | App environment (development/production) |
| `HOST`                 | `0.0.0.0`                                    | Server bind address                      |
| `PORT`                 | `8000`                                       | Server port                              |
| `MCP_BASE_URL`         | `http://localhost:8001`                      | MCP server base URL                      |
| `MCP_TIMEOUT`          | `30`                                         | MCP request timeout in seconds           |
| `GOOGLE_CLIENT_ID`     | -                                            | Google OAuth Client ID                   |
| `GOOGLE_CLIENT_SECRET` | -                                            | Google OAuth Client Secret               |
| `GOOGLE_REDIRECT_URI`  | -                                            | OAuth callback URL for your frontend     |
| `CORS_ORIGINS`         | `http://localhost:3000,http://localhost:8080`| Comma-separated list of allowed origins  |
| `RATE_LIMIT_REQUESTS`  | `100`                                        | Max requests per rate limit window       |
| `RATE_LIMIT_WINDOW`    | `60`                                         | Rate limit window in seconds             |

## Architecture

### Request Flow

```
Client Request
    ↓
RequestID Middleware (tracking)
    ↓
CORS Middleware
    ↓
Route Handler (validate with Pydantic)
    ↓
MCPClient (async HTTP request)
    ↓
MCP Server
    ↓
Response (ExecuteResponse schema)
    ↓
Client
```

### Key Components

**MCPClient** (`app/clients/mcp_client.py`)

- Manages HTTP communication with MCP server
- Handles timeouts and errors gracefully
- Validates responses against Pydantic schemas

**Schemas** (`app/schemas/`)

- `ExecuteRequest`: Validates incoming messages
- `ExecuteResponse`: Structures outgoing responses
- `HealthResponse`: Health check response format
- `ErrorResponse`: Standardized error format

**Middleware** (`app/middleware/`)

- `RequestIDMiddleware`: Adds unique request ID to all requests for tracing
- `SecurityHeadersMiddleware`: Adds security headers (XSS protection, clickjacking prevention, MIME sniffing protection)

## Security Features

- **Security Headers**: Automatic injection of security headers on all responses
  - `X-Content-Type-Options: nosniff` - Prevents MIME sniffing attacks
  - `X-Frame-Options: DENY` - Prevents clickjacking
  - `X-XSS-Protection: 1; mode=block` - XSS protection for older browsers
  - `Referrer-Policy: strict-origin-when-cross-origin` - Privacy protection
  - `Permissions-Policy` - Disables sensitive features (geolocation, microphone, camera)
- **Non-root Docker User**: Container runs as unprivileged `appuser` for enhanced security
- **Configurable CORS**: Explicit origin allowlist instead of wildcard

## Design Principles

1. **Minimal & Clean**: No unnecessary abstractions
2. **Type-Safe**: Full type hints with Pydantic validation
3. **Observable**: Request IDs and structured logging
4. **Secure by Default**: Security headers, non-root containers, explicit CORS
5. **Production-Ready**: Error handling, timeouts, health checks

## Troubleshooting

### OAuth Token Exchange Error

**Error:** `Failed to exchange authorization code for tokens`

**Cause:** In Next.js 15+ with React Strict Mode (enabled by default in development), `useEffect` runs twice. This causes the OAuth callback page to send the authorization code to the backend twice. Since Google authorization codes are single-use, the second request fails.

**Solution:** The frontend callback page (`/auth/youtube/callback`) includes a `useRef` guard to prevent duplicate processing:

```tsx
const hasProcessedRef = useRef(false);

useEffect(() => {
  if (hasProcessedRef.current) return;
  hasProcessedRef.current = true;
  // ... OAuth processing
}, []);
```

### Redirect URI Mismatch

Ensure your `GOOGLE_REDIRECT_URI` in `.env` exactly matches:
1. The redirect URI registered in Google Cloud Console
2. The frontend callback URL (e.g., `http://localhost:3000/auth/youtube/callback`)

## Future Enhancements

The following features are intentionally not implemented but can be added:

- Full user authentication & authorization
- Request/response caching
- Advanced error handling and retry logic
- Comprehensive monitoring and metrics
- Request logging and audit trails
- Token refresh automation for YouTube OAuth
- Active rate limiting enforcement (configuration ready)

## Contributing

When extending this API:

1. Keep the structure clean and logical
2. Add proper type hints and docstrings
3. Validate with Pydantic schemas
4. Include logging for debugging
5. Add tests for new features

## License

Internal Use Only
