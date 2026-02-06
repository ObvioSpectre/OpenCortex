from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.api.auth import parse_auth_context


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.auth_context = parse_auth_context(request)

        if request.url.path.startswith("/chat") and request.state.auth_context is None:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "x-user-id, x-organization-id, and x-role headers are required for chat/query requests"
                },
            )

        return await call_next(request)
