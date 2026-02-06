from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    organization_id: str
    role: str


def parse_auth_context(request: Request) -> AuthContext | None:
    user_id = request.headers.get("x-user-id")
    organization_id = request.headers.get("x-organization-id")
    role = request.headers.get("x-role")
    if user_id and organization_id and role:
        return AuthContext(user_id=user_id, organization_id=organization_id, role=role)
    return None


def require_auth_context(request: Request) -> AuthContext:
    auth_context = getattr(request.state, "auth_context", None)
    if auth_context is None:
        raise HTTPException(
            status_code=401,
            detail="Missing auth context headers: x-user-id, x-organization-id, and x-role are required",
        )
    return auth_context
