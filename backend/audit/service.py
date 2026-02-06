from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models import AuditLog


def record_audit_log(
    session: Session,
    organization_id: str,
    user_id: str,
    role: str,
    data_source_id: str,
    question: str,
    metrics_accessed: List[str],
    access_denied: bool,
    denial_reason: str | None = None,
) -> AuditLog:
    row = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        data_source_id=data_source_id,
        question=question,
        metrics_accessed=metrics_accessed,
        access_denied=access_denied,
        denial_reason=denial_reason,
    )
    session.add(row)
    session.flush()
    return row


def list_audit_logs(session: Session, organization_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    rows = session.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    ).all()

    return [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "user_id": r.user_id,
            "role": r.role,
            "data_source_id": r.data_source_id,
            "question": r.question,
            "metrics_accessed": r.metrics_accessed,
            "access_denied": r.access_denied,
            "denial_reason": r.denial_reason,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
