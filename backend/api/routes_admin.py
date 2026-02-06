from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.audit.service import list_audit_logs
from backend.api.deps import vector_index_service
from backend.db.allowlist import (
    create_organization,
    create_role,
    create_user,
    get_allowlist,
    get_allowlist_with_visibility,
    get_data_source,
    list_organizations,
    list_roles,
    list_users,
    register_vector_index,
    set_allowlist,
    upsert_data_source,
)
from backend.db.mysql import get_mysql_engine, introspect_schema
from backend.db.session import db_session
from backend.models import (
    AllowlistRequest,
    ConnectRequest,
    CreateOrganizationRequest,
    CreateRoleRequest,
    CreateUserRequest,
    DataSource,
    SemanticVisibilityOverrideRequest,
)
from backend.semantic.service import SemanticService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/organizations")
def create_organization_endpoint(payload: CreateOrganizationRequest):
    with db_session() as session:
        org = create_organization(session, payload.id, payload.name)
        return {
            "organization": {
                "id": org.id,
                "name": org.name,
                "status": org.status,
                "created_at": org.created_at.isoformat(),
            }
        }


@router.get("/organizations")
def list_organizations_endpoint():
    with db_session() as session:
        orgs = list_organizations(session)
        return {
            "organizations": [
                {
                    "id": o.id,
                    "name": o.name,
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orgs
            ]
        }


@router.post("/roles")
def create_role_endpoint(payload: CreateRoleRequest):
    with db_session() as session:
        role = create_role(session, payload.organization_id, payload.role_key, payload.description, payload.is_active)
        return {
            "role": {
                "id": role.id,
                "organization_id": role.organization_id,
                "role_key": role.role_key,
                "description": role.description,
                "is_active": role.is_active,
            }
        }


@router.get("/organizations/{organization_id}/roles")
def list_roles_endpoint(organization_id: str):
    with db_session() as session:
        roles = list_roles(session, organization_id)
        return {
            "roles": [
                {
                    "id": r.id,
                    "organization_id": r.organization_id,
                    "role_key": r.role_key,
                    "description": r.description,
                    "is_active": r.is_active,
                }
                for r in roles
            ]
        }


@router.post("/users")
def create_user_endpoint(payload: CreateUserRequest):
    with db_session() as session:
        user = create_user(session, payload.user_id, payload.organization_id, payload.role, payload.status)
        return {
            "user": {
                "user_id": user.user_id,
                "organization_id": user.organization_id,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            }
        }


@router.get("/organizations/{organization_id}/users")
def list_users_endpoint(organization_id: str):
    with db_session() as session:
        users = list_users(session, organization_id)
        return {
            "users": [
                {
                    "user_id": u.user_id,
                    "organization_id": u.organization_id,
                    "role": u.role,
                    "status": u.status,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
        }


@router.get("/organizations/{organization_id}/audit-logs")
def list_audit_logs_endpoint(organization_id: str, limit: int = 200):
    with db_session() as session:
        return {"audit_logs": list_audit_logs(session, organization_id, limit=limit)}


@router.post("/data-sources/connect")
def connect_data_source(payload: ConnectRequest):
    with db_session() as session:
        upsert_data_source(session, payload.id, payload.organization_id, payload.name, payload.mysql_uri)
        engine = get_mysql_engine(payload.id, payload.mysql_uri)
        schema = introspect_schema(engine)
    return {
        "status": "connected",
        "organization_id": payload.organization_id,
        "data_source_id": payload.id,
        "schema": schema,
    }


@router.get("/organizations/{organization_id}/data-sources")
def list_data_sources(organization_id: str):
    with db_session() as session:
        rows = session.scalars(select(DataSource).where(DataSource.organization_id == organization_id)).all()
        return {
            "data_sources": [
                {
                    "id": r.id,
                    "organization_id": r.organization_id,
                    "name": r.name,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        }


@router.get("/data-sources/{data_source_id}/schema")
def get_schema(data_source_id: str):
    with db_session() as session:
        ds = get_data_source(session, data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")
        engine = get_mysql_engine(ds.id, ds.mysql_uri)
        schema = introspect_schema(engine)
        return {"organization_id": ds.organization_id, "schema": schema}


@router.post("/allowlist")
def save_allowlist(payload: AllowlistRequest):
    with db_session() as session:
        ds = get_data_source(session, payload.data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")
        if ds.organization_id != payload.organization_id:
            raise HTTPException(status_code=400, detail="organization_id does not own data source")
        set_allowlist(session, payload)
        return {"status": "ok"}


@router.get("/data-sources/{data_source_id}/allowlist")
def fetch_allowlist(data_source_id: str):
    with db_session() as session:
        return get_allowlist_with_visibility(session, data_source_id)


@router.post("/data-sources/{data_source_id}/semantic/build")
def build_semantic_model(data_source_id: str):
    with db_session() as session:
        ds = get_data_source(session, data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")

        allowlist = get_allowlist(session, data_source_id)
        if not allowlist:
            raise HTTPException(status_code=400, detail="Allowlist is empty")

        engine = get_mysql_engine(ds.id, ds.mysql_uri)
        schema = introspect_schema(engine)

        semantic_service = SemanticService()
        semantic_model = semantic_service.build_semantic_model(session, ds.organization_id, data_source_id, schema, allowlist)
        return {"organization_id": ds.organization_id, **semantic_model}


@router.get("/data-sources/{data_source_id}/semantic")
def get_semantic_model(data_source_id: str):
    with db_session() as session:
        ds = get_data_source(session, data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")
        semantic_service = SemanticService()
        semantic = semantic_service.get_semantics(session, ds.organization_id, data_source_id)
        return {"organization_id": ds.organization_id, **semantic}


@router.post("/data-sources/{data_source_id}/semantic/visibility")
def override_semantic_visibility(data_source_id: str, payload: SemanticVisibilityOverrideRequest):
    with db_session() as session:
        ds = get_data_source(session, data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")
        if ds.organization_id != payload.organization_id:
            raise HTTPException(status_code=400, detail="organization_id does not own data source")

        semantic_service = SemanticService()
        semantic = semantic_service.apply_visibility_overrides(
            session=session,
            organization_id=payload.organization_id,
            data_source_id=data_source_id,
            payload=payload,
        )
        return {"organization_id": ds.organization_id, **semantic}


@router.post("/data-sources/{data_source_id}/vector/index")
def index_semantic_docs(data_source_id: str):
    with db_session() as session:
        ds = get_data_source(session, data_source_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Data source not found")

        semantic_service = SemanticService()
        semantic = semantic_service.get_semantics(session, ds.organization_id, data_source_id)
        docs = vector_index_service.build_semantic_docs(data_source_id, semantic)

        collection = f"org:{ds.organization_id}:semantic:{data_source_id}"
        register_vector_index(session, ds.organization_id, data_source_id, collection)

    count = vector_index_service.index_documents(collection=collection, docs=docs)
    return {
        "organization_id": ds.organization_id,
        "indexed": count,
        "collection": collection,
    }
