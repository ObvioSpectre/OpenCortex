# Conversational BI Platform (Internal Release)

Production-oriented conversational BI platform with organization governance, semantic permissions, SQL hard guardrails, and auditability.

## Core capabilities

- MySQL onboarding with schema introspection (databases/tables/columns/types/PK/FK/date-time)
- Organization model with users and configurable roles
- Role-based table/column allowlist and semantic visibility (table/column/metric)
- Metadata-only vector indexing (no raw row embeddings)
- Read-only text-to-SQL pipeline with SQL hard validation before execution
- Executive insight generation with safe fallback when access is restricted
- Admin UI for governance and configuration
- Full audit logging for chat access events

## Project structure

- `/Users/apple/Documents/vector_db_chatbot/backend/db` - datasource onboarding, allowlist storage
- `/Users/apple/Documents/vector_db_chatbot/backend/semantic` - semantic generation, visibility, overrides
- `/Users/apple/Documents/vector_db_chatbot/backend/vector` - vector indexing/retrieval, role filtering
- `/Users/apple/Documents/vector_db_chatbot/backend/agent` - intent, SQL generation, SQL validation, insights
- `/Users/apple/Documents/vector_db_chatbot/backend/audit` - audit log persistence/query
- `/Users/apple/Documents/vector_db_chatbot/backend/api` - admin/chat APIs + auth middleware
- `/Users/apple/Documents/vector_db_chatbot/frontend` - React admin + chat UI

## Data governance model

### Organizations
- Own data sources, semantic definitions, vector indexes, users, and roles.

### Roles
Default role keys seeded per organization:
- `admin`
- `executive`
- `senior_executive`
- `finance`
- `sales`

Roles are configurable via admin APIs.

### Users
Fields:
- `user_id`
- `organization_id`
- `role`
- `status` (`active`/`inactive`)

### Semantic permissions
Role visibility is persisted for:
- tables (`allowlist_tables.allowed_roles`)
- columns (`allowlist_columns.allowed_roles`, `semantic_columns.allowed_roles`)
- metrics (`metric_definitions.allowed_roles`)

## Authentication context (required for chat)

Headers required on every `/chat/*` request:
- `x-user-id`
- `x-organization-id`
- `x-role`

Request body fields must match header context.

## Security guarantees

- Only read-only SQL is executable.
- SQL validation is independent of the LLM.
- Guardrail validates every referenced table and column against role allowlist.
- Subqueries are parsed and validated (restricted table in subquery is blocked).
- `SELECT *` and `table.*` are blocked.
- Multiple statements and DDL/DML are blocked.
- Vector retrieval is role-filtered; disallowed semantic docs are not surfaced to LLM.
- Raw MySQL rows are never embedded.
- Chat response does not expose SQL or permission internals.

## Audit log schema

Table: `audit_logs`

Captured fields:
- `organization_id`
- `user_id`
- `role`
- `data_source_id`
- `question`
- `metrics_accessed` (list)
- `access_denied` (boolean)
- `denial_reason`
- `created_at`

## Admin endpoints

### Organization/Identity
- `POST /admin/organizations`
- `GET /admin/organizations`
- `POST /admin/roles`
- `GET /admin/organizations/{organization_id}/roles`
- `POST /admin/users`
- `GET /admin/organizations/{organization_id}/users`

### Data onboarding and access
- `POST /admin/data-sources/connect`
- `GET /admin/organizations/{organization_id}/data-sources`
- `POST /admin/allowlist`
- `GET /admin/data-sources/{data_source_id}/allowlist`

### Semantic and vector
- `POST /admin/data-sources/{data_source_id}/semantic/build`
- `GET /admin/data-sources/{data_source_id}/semantic`
- `POST /admin/data-sources/{data_source_id}/semantic/visibility`
- `POST /admin/data-sources/{data_source_id}/vector/index`

### Audit
- `GET /admin/organizations/{organization_id}/audit-logs`

## Chat behavior

- SQL is never returned to leader chat clients.
- Permission details are not exposed.
- Restricted-access response is polite and generic:
  - `I can't provide that data right now.`

## Final validation matrix

Validated in tests:
- Executive cannot access revenue metric (`orders_revenue_sum` not visible)
- Finance can access revenue metric
- Admin can access all metrics visible to executive and finance

See:
- `/Users/apple/Documents/vector_db_chatbot/backend/tests/test_role_access_validation.py`

## Setup

### Backend

```bash
cd /Users/apple/Documents/vector_db_chatbot/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

If migrating from older schema versions, recreate `metadata.db`.

### Frontend

```bash
cd /Users/apple/Documents/vector_db_chatbot/frontend
npm install
npm run dev
```

### Sample MySQL

```bash
cd /Users/apple/Documents/vector_db_chatbot
docker compose up -d
```

Datasource example:
- `mysql+pymysql://readonly:readonly@localhost:3306/analytics`

## Tests

```bash
cd /Users/apple/Documents/vector_db_chatbot
PYTHONPATH=/Users/apple/Documents/vector_db_chatbot PYTHONPYCACHEPREFIX=/tmp/pycache backend/.venv/bin/pytest -q backend/tests
```
