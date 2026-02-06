from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Set

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    AllowlistColumn,
    AllowlistRequest,
    AllowlistTable,
    DataSource,
    MetricDefinition,
    Organization,
    OrganizationRole,
    OrganizationUser,
    SemanticColumn,
    VectorIndex,
)

DEFAULT_ROLES = ["admin", "executive", "senior_executive", "finance", "sales"]


def create_organization(session: Session, organization_id: str, name: str) -> Organization:
    existing = session.get(Organization, organization_id)
    if existing:
        existing.name = name
        org = existing
    else:
        org = Organization(id=organization_id, name=name, status="active")
        session.add(org)
        session.flush()

    _ensure_default_roles(session, organization_id)
    return org


def list_organizations(session: Session) -> list[Organization]:
    return session.scalars(select(Organization)).all()


def create_role(session: Session, organization_id: str, role_key: str, description: str = "", is_active: bool = True) -> OrganizationRole:
    role = session.scalars(
        select(OrganizationRole).where(
            OrganizationRole.organization_id == organization_id,
            OrganizationRole.role_key == role_key,
        )
    ).first()
    if role:
        role.description = description
        role.is_active = is_active
        return role

    role = OrganizationRole(
        organization_id=organization_id,
        role_key=role_key,
        description=description,
        is_active=is_active,
    )
    session.add(role)
    return role


def list_roles(session: Session, organization_id: str) -> list[OrganizationRole]:
    return session.scalars(select(OrganizationRole).where(OrganizationRole.organization_id == organization_id)).all()


def list_active_role_keys(session: Session, organization_id: str) -> list[str]:
    roles = session.scalars(
        select(OrganizationRole).where(
            OrganizationRole.organization_id == organization_id,
            OrganizationRole.is_active.is_(True),
        )
    ).all()
    return [r.role_key for r in roles]


def create_user(session: Session, user_id: str, organization_id: str, role: str, status: str = "active") -> OrganizationUser:
    user = session.get(OrganizationUser, user_id)
    if user:
        user.organization_id = organization_id
        user.role = role
        user.status = status
        return user

    user = OrganizationUser(user_id=user_id, organization_id=organization_id, role=role, status=status)
    session.add(user)
    return user


def list_users(session: Session, organization_id: str) -> list[OrganizationUser]:
    return session.scalars(select(OrganizationUser).where(OrganizationUser.organization_id == organization_id)).all()


def upsert_data_source(session: Session, data_source_id: str, organization_id: str, name: str, mysql_uri: str) -> DataSource:
    ds = session.get(DataSource, data_source_id)
    if ds is None:
        ds = DataSource(id=data_source_id, organization_id=organization_id, name=name, mysql_uri=mysql_uri)
        session.add(ds)
    else:
        ds.organization_id = organization_id
        ds.name = name
        ds.mysql_uri = mysql_uri
    session.flush()
    return ds


def get_data_source(session: Session, data_source_id: str) -> DataSource | None:
    return session.get(DataSource, data_source_id)


def set_allowlist(session: Session, request: AllowlistRequest) -> None:
    default_roles = list_active_role_keys(session, request.organization_id) or DEFAULT_ROLES
    existing = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == request.data_source_id)).all()
    for table in existing:
        session.execute(delete(AllowlistColumn).where(AllowlistColumn.allowlist_table_id == table.id))
    session.execute(delete(AllowlistTable).where(AllowlistTable.data_source_id == request.data_source_id))

    for table_payload in request.tables:
        table = AllowlistTable(
            data_source_id=request.data_source_id,
            database_name=table_payload.database_name,
            table_name=table_payload.table_name,
            approved=True,
            allowed_roles=default_roles,
        )
        session.add(table)
        session.flush()
        for column_name in table_payload.approved_columns:
            session.add(
                AllowlistColumn(
                    allowlist_table_id=table.id,
                    column_name=column_name,
                    approved=True,
                    allowed_roles=default_roles,
                )
            )


def get_allowlist(session: Session, data_source_id: str) -> Dict[str, Set[str]]:
    tables = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == data_source_id)).all()
    output: Dict[str, Set[str]] = {}
    for table in tables:
        key = f"{table.database_name}.{table.table_name}"
        columns = session.scalars(select(AllowlistColumn.column_name).where(AllowlistColumn.allowlist_table_id == table.id)).all()
        output[key] = set(columns)
    return output


def get_role_scoped_allowlist(session: Session, data_source_id: str, role: str) -> Dict[str, Set[str]]:
    tables = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == data_source_id)).all()
    output: Dict[str, Set[str]] = {}
    for table in tables:
        table_roles = table.allowed_roles or []
        if table_roles and role not in table_roles:
            continue
        key = f"{table.database_name}.{table.table_name}"
        cols = session.scalars(select(AllowlistColumn).where(AllowlistColumn.allowlist_table_id == table.id)).all()
        allowed_cols = {c.column_name for c in cols if (not c.allowed_roles) or role in c.allowed_roles}
        if allowed_cols:
            output[key] = allowed_cols
    return output


def allowlist_to_json(allowlist: Dict[str, Set[str]]) -> Dict[str, Any]:
    tables = []
    for fully_qualified_table, cols in sorted(allowlist.items()):
        database_name, table_name = fully_qualified_table.split(".", 1)
        tables.append(
            {
                "database_name": database_name,
                "table_name": table_name,
                "approved_columns": sorted(list(cols)),
            }
        )
    return {"tables": tables}


def get_allowlist_with_visibility(session: Session, data_source_id: str) -> Dict[str, Any]:
    tables = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == data_source_id)).all()
    payload = []
    for table in tables:
        columns = session.scalars(select(AllowlistColumn).where(AllowlistColumn.allowlist_table_id == table.id)).all()
        payload.append(
            {
                "database_name": table.database_name,
                "table_name": table.table_name,
                "table_allowed_roles": table.allowed_roles or [],
                "approved_columns": [c.column_name for c in columns],
                "column_visibility": [
                    {"column_name": c.column_name, "allowed_roles": c.allowed_roles or []}
                    for c in columns
                ],
            }
        )
    return {"tables": payload}


def apply_table_visibility_override(
    session: Session,
    data_source_id: str,
    database_name: str,
    table_name: str,
    allowed_roles: list[str],
) -> None:
    table = session.scalars(
        select(AllowlistTable).where(
            AllowlistTable.data_source_id == data_source_id,
            AllowlistTable.database_name == database_name,
            AllowlistTable.table_name == table_name,
        )
    ).first()
    if table:
        table.allowed_roles = allowed_roles


def apply_column_visibility_override(
    session: Session,
    data_source_id: str,
    database_name: str,
    table_name: str,
    column_name: str,
    allowed_roles: list[str],
) -> None:
    table = session.scalars(
        select(AllowlistTable).where(
            AllowlistTable.data_source_id == data_source_id,
            AllowlistTable.database_name == database_name,
            AllowlistTable.table_name == table_name,
        )
    ).first()
    if not table:
        return
    col = session.scalars(
        select(AllowlistColumn).where(
            AllowlistColumn.allowlist_table_id == table.id,
            AllowlistColumn.column_name == column_name,
        )
    ).first()
    if col:
        col.allowed_roles = allowed_roles


def register_vector_index(session: Session, organization_id: str, data_source_id: str, collection_name: str) -> VectorIndex:
    record = session.scalars(
        select(VectorIndex).where(
            VectorIndex.organization_id == organization_id,
            VectorIndex.data_source_id == data_source_id,
            VectorIndex.collection_name == collection_name,
        )
    ).first()

    if record:
        record.last_indexed_at = datetime.utcnow()
        record.provider = settings.vector_provider
        return record

    record = VectorIndex(
        organization_id=organization_id,
        data_source_id=data_source_id,
        collection_name=collection_name,
        provider=settings.vector_provider,
        last_indexed_at=datetime.utcnow(),
    )
    session.add(record)
    return record


def list_vector_indexes(session: Session, organization_id: str, data_source_id: str | None = None) -> list[VectorIndex]:
    stmt = select(VectorIndex).where(VectorIndex.organization_id == organization_id)
    if data_source_id:
        stmt = stmt.where(VectorIndex.data_source_id == data_source_id)
    return session.scalars(stmt).all()


def _ensure_default_roles(session: Session, organization_id: str) -> None:
    existing = {
        r.role_key
        for r in session.scalars(
            select(OrganizationRole).where(OrganizationRole.organization_id == organization_id)
        ).all()
    }
    for role_key in DEFAULT_ROLES:
        if role_key not in existing:
            session.add(
                OrganizationRole(
                    organization_id=organization_id,
                    role_key=role_key,
                    description=f"Default organization role: {role_key}",
                    is_active=True,
                )
            )


def delete_semantic_for_datasource(session: Session, organization_id: str, data_source_id: str) -> None:
    session.execute(
        delete(SemanticColumn).where(
            SemanticColumn.organization_id == organization_id,
            SemanticColumn.data_source_id == data_source_id,
        )
    )
    session.execute(
        delete(MetricDefinition).where(
            MetricDefinition.organization_id == organization_id,
            MetricDefinition.data_source_id == data_source_id,
        )
    )
