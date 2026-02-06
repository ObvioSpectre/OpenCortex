from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.audit.service import record_audit_log
from backend.api.auth import require_auth_context
from backend.api.deps import query_pipeline
from backend.db.session import db_session
from backend.models import AskRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask")
def ask_question(payload: AskRequest, request: Request):
    try:
        auth_context = require_auth_context(request)
        if (
            auth_context.organization_id != payload.organization_id
            or auth_context.role != payload.role
            or auth_context.user_id != payload.user_id
        ):
            raise HTTPException(status_code=400, detail="Auth header context must match request user_id, organization_id, and role")

        with db_session() as session:
            result = query_pipeline.run(
                session=session,
                user_id=payload.user_id,
                organization_id=payload.organization_id,
                role=payload.role,
                data_source_id=payload.data_source_id,
                question=payload.question,
                show_sql=payload.show_sql,
            )

            audit = result.pop("_audit", None)
            if audit:
                record_audit_log(session=session, **audit)

            result["sql"] = None
            result.pop("debug", None)
            return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {exc}") from exc
