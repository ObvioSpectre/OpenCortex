from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    data_sources: Mapped[List["DataSource"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    roles: Mapped[List["OrganizationRole"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    users: Mapped[List["OrganizationUser"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class OrganizationRole(Base):
    __tablename__ = "organization_roles"
    __table_args__ = (UniqueConstraint("organization_id", "role_key", name="uq_org_role"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    role_key: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped[Organization] = relationship(back_populates="roles")


class OrganizationUser(Base):
    __tablename__ = "organization_users"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="users")


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_data_source_org_name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    mysql_uri: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="data_sources")
    allowlist_tables: Mapped[List["AllowlistTable"]] = relationship(back_populates="data_source", cascade="all, delete-orphan")


class AllowlistTable(Base):
    __tablename__ = "allowlist_tables"
    __table_args__ = (UniqueConstraint("data_source_id", "database_name", "table_name", name="uq_allowlist_table"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"))
    database_name: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_roles: Mapped[List[str]] = mapped_column(JSON, default=list)

    data_source: Mapped[DataSource] = relationship(back_populates="allowlist_tables")
    columns: Mapped[List["AllowlistColumn"]] = relationship(back_populates="table", cascade="all, delete-orphan")


class AllowlistColumn(Base):
    __tablename__ = "allowlist_columns"
    __table_args__ = (UniqueConstraint("allowlist_table_id", "column_name", name="uq_allowlist_column"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    allowlist_table_id: Mapped[int] = mapped_column(ForeignKey("allowlist_tables.id", ondelete="CASCADE"))
    column_name: Mapped[str] = mapped_column(String(255))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_roles: Mapped[List[str]] = mapped_column(JSON, default=list)

    table: Mapped[AllowlistTable] = relationship(back_populates="columns")


class SemanticColumn(Base):
    __tablename__ = "semantic_columns"
    __table_args__ = (
        UniqueConstraint("organization_id", "data_source_id", "database_name", "table_name", "column_name", name="uq_semantic_col"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True)
    data_source_id: Mapped[str] = mapped_column(String(64), index=True)
    database_name: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    column_name: Mapped[str] = mapped_column(String(255))
    semantic_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    metric_candidates: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    allowed_roles: Mapped[List[str]] = mapped_column(JSON, default=list)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "data_source_id", "name", name="uq_metric_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True)
    data_source_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    expression_sql: Mapped[str] = mapped_column(Text)
    meta: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    allowed_roles: Mapped[List[str]] = mapped_column(JSON, default=list)


class VectorIndex(Base):
    __tablename__ = "vector_indexes"
    __table_args__ = (UniqueConstraint("organization_id", "data_source_id", "collection_name", name="uq_vector_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True)
    data_source_id: Mapped[str] = mapped_column(String(64), index=True)
    collection_name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(64), default="memory")
    last_indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    data_source_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    metrics_accessed: Mapped[List[str]] = mapped_column(JSON, default=list)
    access_denied: Mapped[bool] = mapped_column(Boolean, default=False)
    denial_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CreateOrganizationRequest(BaseModel):
    id: str = Field(min_length=2, max_length=64)
    name: str


class CreateRoleRequest(BaseModel):
    organization_id: str
    role_key: str
    description: str = ""
    is_active: bool = True


class CreateUserRequest(BaseModel):
    user_id: str
    organization_id: str
    role: str
    status: str = "active"


class ConnectRequest(BaseModel):
    id: str = Field(min_length=2, max_length=64)
    organization_id: str
    name: str
    mysql_uri: str = Field(description="MySQL SQLAlchemy URI e.g. mysql+pymysql://user:pass@host:3306/db")


class DataSourceResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    created_at: datetime


class AllowlistTablePayload(BaseModel):
    database_name: str
    table_name: str
    approved_columns: List[str]


class SemanticTableVisibilityOverride(BaseModel):
    database_name: str
    table_name: str
    allowed_roles: List[str]


class SemanticColumnVisibilityOverride(BaseModel):
    database_name: str
    table_name: str
    column_name: str
    allowed_roles: List[str]


class SemanticMetricVisibilityOverride(BaseModel):
    metric_name: str
    allowed_roles: List[str]


class AllowlistRequest(BaseModel):
    organization_id: str
    data_source_id: str
    tables: List[AllowlistTablePayload]


class SemanticVisibilityOverrideRequest(BaseModel):
    organization_id: str
    table_overrides: List[SemanticTableVisibilityOverride] = Field(default_factory=list)
    column_overrides: List[SemanticColumnVisibilityOverride] = Field(default_factory=list)
    metric_overrides: List[SemanticMetricVisibilityOverride] = Field(default_factory=list)


class AskRequest(BaseModel):
    user_id: str
    organization_id: str
    role: str
    data_source_id: str
    question: str
    show_sql: bool = False


class InsightResponse(BaseModel):
    executive_summary: str
    key_insights: List[str]
    recommendations: List[str]
    limitations: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    sql: Optional[str]
    rows: List[Dict[str, Any]]
    insight: InsightResponse
