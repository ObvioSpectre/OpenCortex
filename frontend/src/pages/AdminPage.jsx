import React, { useMemo, useState } from 'react'
import { SchemaApprovalCard } from '../components/admin/SchemaApprovalCard'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { DataTable } from '../components/ui/DataTable'
import { Modal } from '../components/ui/Modal'
import { Tabs } from '../components/ui/Tabs'
import { Toggle } from '../components/ui/Toggle'
import { api } from '../services/api'

const DEFAULT_ROLES = ['executive', 'finance', 'admin']

export function AdminPage() {
  const [organizationId, setOrganizationId] = useState('org_demo')
  const [dataSourceId, setDataSourceId] = useState('default_mysql')
  const [dataSourceName, setDataSourceName] = useState('Primary MySQL')
  const [mysqlUri, setMysqlUri] = useState('mysql+pymysql://readonly:readonly@localhost:3306/analytics')

  const [schema, setSchema] = useState(null)
  const [selected, setSelected] = useState({})
  const [roles, setRoles] = useState([])
  const [users, setUsers] = useState([])
  const [status, setStatus] = useState('Ready')

  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [userModalOpen, setUserModalOpen] = useState(false)
  const [newRole, setNewRole] = useState('finance')
  const [newUserId, setNewUserId] = useState('alice')
  const [newUserRole, setNewUserRole] = useState('executive')

  const [semanticRoleTab, setSemanticRoleTab] = useState('executive')
  const [metricVisibility, setMetricVisibility] = useState({
    orders_revenue_sum: ['admin', 'finance'],
    orders_quantity_sum: ['admin', 'executive', 'sales'],
  })
  const [tableVisibility, setTableVisibility] = useState({
    'analytics.orders': ['admin', 'executive', 'finance', 'sales'],
  })
  const [columnVisibility, setColumnVisibility] = useState({
    'analytics.orders.revenue': ['admin', 'finance'],
    'analytics.orders.quantity': ['admin', 'executive', 'sales', 'finance'],
  })

  const stepStatus = useMemo(() => ({
    connect: !!schema,
    review: !!schema,
    approve: Object.keys(selected).length > 0,
    semantic: false,
    vector: false,
  }), [schema, selected])

  const roleTabs = roles.length ? roles.map((r) => r.role_key) : DEFAULT_ROLES

  const onToggle = (databaseName, tableName, columnName, checked) => {
    const key = `${databaseName}.${tableName}`
    const next = { ...selected }

    if (!columnName) {
      if (checked) {
        const table = schema.databases
          .find((db) => db.database_name === databaseName)
          ?.tables.find((t) => t.table_name === tableName)
        next[key] = new Set(table?.columns.map((c) => c.name) || [])
      } else {
        delete next[key]
      }
      setSelected(next)
      return
    }

    if (!next[key]) next[key] = new Set()
    if (checked) next[key].add(columnName)
    else next[key].delete(columnName)
    if (next[key].size === 0) delete next[key]
    setSelected(next)
  }

  const createOrg = async () => {
    try {
      await api.createOrganization({ id: organizationId, name: organizationId })
      setStatus('Organization is active.')
    } catch (e) {
      setStatus(`Organization error: ${e.message}`)
    }
  }

  const loadGovernance = async () => {
    try {
      const [roleRes, userRes] = await Promise.all([api.listRoles(organizationId), api.listUsers(organizationId)])
      setRoles(roleRes.roles || [])
      setUsers(userRes.users || [])
      setStatus('Roles and users loaded.')
    } catch (e) {
      setStatus(`Governance load failed: ${e.message}`)
    }
  }

  const saveRole = async () => {
    try {
      await api.createRole({ organization_id: organizationId, role_key: newRole, description: `Role ${newRole}`, is_active: true })
      setRoleModalOpen(false)
      await loadGovernance()
    } catch (e) {
      setStatus(`Role error: ${e.message}`)
    }
  }

  const saveUser = async () => {
    try {
      await api.createUser({ user_id: newUserId, organization_id: organizationId, role: newUserRole, status: 'active' })
      setUserModalOpen(false)
      await loadGovernance()
    } catch (e) {
      setStatus(`User error: ${e.message}`)
    }
  }

  const connect = async () => {
    try {
      const res = await api.connectDataSource({ id: dataSourceId, organization_id: organizationId, name: dataSourceName, mysql_uri: mysqlUri })
      setSchema(res.schema)
      setStatus('Database connected and schema loaded.')
    } catch (e) {
      setStatus(`Connection failed: ${e.message}`)
    }
  }

  const saveAllowlist = async () => {
    try {
      const tables = Object.entries(selected).map(([key, cols]) => {
        const [database_name, table_name] = key.split('.')
        return { database_name, table_name, approved_columns: Array.from(cols) }
      })
      await api.saveAllowlist({ organization_id: organizationId, data_source_id: dataSourceId, tables })
      setStatus('Table and column access approved.')
    } catch (e) {
      setStatus(`Allowlist save failed: ${e.message}`)
    }
  }

  const buildSemantic = async () => {
    try {
      await api.buildSemantic(dataSourceId)
      setStatus('Semantic layer generated.')
    } catch (e) {
      setStatus(`Semantic build failed: ${e.message}`)
    }
  }

  const indexVectors = async () => {
    try {
      await api.indexVectors(dataSourceId)
      setStatus('Vector index completed.')
    } catch (e) {
      setStatus(`Vector indexing failed: ${e.message}`)
    }
  }

  const applyVisibility = async () => {
    try {
      const role = semanticRoleTab
      const tableOverrides = Object.entries(tableVisibility).map(([fqTable, allowed]) => {
        const [database_name, table_name] = fqTable.split('.')
        return {
          database_name,
          table_name,
          allowed_roles: allowed.filter((r) => r === role || r !== role),
        }
      })

      const columnOverrides = Object.entries(columnVisibility).map(([fqColumn, allowed]) => {
        const [database_name, table_name, column_name] = fqColumn.split('.')
        return {
          database_name,
          table_name,
          column_name,
          allowed_roles: allowed.filter((r) => r === role || r !== role),
        }
      })

      const metricOverrides = Object.entries(metricVisibility).map(([metric_name, allowed_roles]) => ({
        metric_name,
        allowed_roles,
      }))

      await api.overrideSemanticVisibility(dataSourceId, {
        organization_id: organizationId,
        table_overrides: tableOverrides,
        column_overrides: columnOverrides,
        metric_overrides: metricOverrides,
      })
      setStatus('Visibility rules updated.')
    } catch (e) {
      setStatus(`Visibility update failed: ${e.message}`)
    }
  }

  const toggleRole = (current, role) => current.includes(role) ? current.filter((r) => r !== role) : [...current, role]

  const roleRows = roles.map((r) => ({ id: r.id, role: r.role_key, status: r.is_active ? 'Active' : 'Inactive' }))
  const userRows = users.map((u) => ({ id: u.user_id, name: u.user_id, role: u.role, status: u.status }))

  return (
    <div className="section-stack">
      <div className="page-header">
        <div>
          <h2>Admin Console</h2>
          <p>Organization governance, semantic access control, and onboarding workflow.</p>
        </div>
        <Badge tone="success">Workspace Active</Badge>
      </div>

      <Card
        title="Organization"
        subtitle="Define your operating organization and governance context."
        right={<Badge tone="success">Active</Badge>}
      >
        <div className="grid grid-2">
          <input className="input" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="Organization ID" />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button variant="secondary" onClick={loadGovernance}>Refresh Governance</Button>
            <Button onClick={createOrg}>Save Organization</Button>
          </div>
        </div>
      </Card>

      <div className="grid grid-2">
        <Card title="Roles" subtitle="Role catalog for semantic visibility and policy.">
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <div className="pill-wrap">
              {roleTabs.map((r) => <span className="pill" key={r}>{r}</span>)}
            </div>
            <Button onClick={() => setRoleModalOpen(true)}>Add Role</Button>
          </div>
          <DataTable columns={[{ key: 'role', label: 'Role' }, { key: 'status', label: 'Status' }]} rows={roleRows} empty="No roles yet." />
        </Card>

        <Card title="Users" subtitle="User-role assignments for internal access.">
          <div className="row" style={{ justifyContent: 'flex-end', marginBottom: 12 }}>
            <Button onClick={() => setUserModalOpen(true)}>Add User</Button>
          </div>
          <DataTable
            columns={[{ key: 'name', label: 'Name' }, { key: 'role', label: 'Role' }, { key: 'status', label: 'Status' }]}
            rows={userRows}
            empty="No users yet."
          />
        </Card>
      </div>

      <Card title="Data Source Onboarding" subtitle="Step-based flow for secure activation.">
        <div className="step-list" style={{ marginBottom: 14 }}>
          {[
            { id: 'connect', label: 'Connect Database', done: stepStatus.connect, action: connect },
            { id: 'review', label: 'Review Schema', done: stepStatus.review },
            { id: 'approve', label: 'Approve Tables', done: stepStatus.approve, action: saveAllowlist },
            { id: 'semantic', label: 'Build Semantic Layer', done: false, action: buildSemantic },
            { id: 'vector', label: 'Index Vectors', done: false, action: indexVectors },
          ].map((step, index) => (
            <div key={step.id} className="step-item">
              <div className="step-label">
                <span className="step-index">{index + 1}</span>
                <strong>{step.label}</strong>
                {step.done ? <Badge tone="success">Done</Badge> : <Badge tone="neutral">Pending</Badge>}
              </div>
              {step.action ? <Button variant="secondary" onClick={step.action}>{step.done ? 'Run Again' : 'Start'}</Button> : null}
            </div>
          ))}
        </div>

        <div className="grid grid-2" style={{ marginBottom: 12 }}>
          <input className="input" value={dataSourceId} onChange={(e) => setDataSourceId(e.target.value)} placeholder="Data source ID" />
          <input className="input" value={dataSourceName} onChange={(e) => setDataSourceName(e.target.value)} placeholder="Data source name" />
        </div>
        <input className="input" value={mysqlUri} onChange={(e) => setMysqlUri(e.target.value)} placeholder="MySQL URI" />
      </Card>

      <SchemaApprovalCard schema={schema} selected={selected} onToggle={onToggle} />

      <Card title="Visibility & Permissions" subtitle="Role-based control for tables, columns, and metrics.">
        <Tabs tabs={roleTabs} active={semanticRoleTab} onChange={setSemanticRoleTab} />

        <div className="grid grid-2">
          <Card title="Table Access" subtitle={`Visible tables for ${semanticRoleTab}`}>
            {Object.entries(tableVisibility).map(([table, roles]) => (
              <div key={table} className="row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
                <span>{table}</span>
                <Toggle
                  checked={roles.includes(semanticRoleTab)}
                  onChange={() => setTableVisibility((prev) => ({ ...prev, [table]: toggleRole(prev[table], semanticRoleTab) }))}
                />
              </div>
            ))}
          </Card>

          <Card title="Metric Visibility" subtitle={`Executive metrics policy for ${semanticRoleTab}`}>
            {Object.entries(metricVisibility).map(([metric, roles]) => (
              <div key={metric} className="row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
                <span>{metric}</span>
                <Toggle
                  checked={roles.includes(semanticRoleTab)}
                  onChange={() => setMetricVisibility((prev) => ({ ...prev, [metric]: toggleRole(prev[metric], semanticRoleTab) }))}
                />
              </div>
            ))}
          </Card>
        </div>

        <details style={{ marginTop: 12 }}>
          <summary style={{ cursor: 'pointer', color: '#3d4c70' }}>Column-level permissions</summary>
          <div style={{ marginTop: 10 }}>
            {Object.entries(columnVisibility).map(([column, roles]) => (
              <div key={column} className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
                <span>{column}</span>
                <Toggle
                  checked={roles.includes(semanticRoleTab)}
                  onChange={() => setColumnVisibility((prev) => ({ ...prev, [column]: toggleRole(prev[column], semanticRoleTab) }))}
                />
              </div>
            ))}
          </div>
        </details>

        <div className="row" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
          <Button onClick={applyVisibility}>Apply Visibility Rules</Button>
        </div>
      </Card>

      <div className="status-bar">{status}</div>

      <Modal
        open={roleModalOpen}
        title="Add Role"
        onClose={() => setRoleModalOpen(false)}
        footer={<Button onClick={saveRole}>Save Role</Button>}
      >
        <input className="input" value={newRole} onChange={(e) => setNewRole(e.target.value)} placeholder="Role key" />
      </Modal>

      <Modal
        open={userModalOpen}
        title="Add User"
        onClose={() => setUserModalOpen(false)}
        footer={<Button onClick={saveUser}>Save User</Button>}
      >
        <input className="input" value={newUserId} onChange={(e) => setNewUserId(e.target.value)} placeholder="User name/id" />
        <input className="input" value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)} placeholder="Assigned role" />
      </Modal>
    </div>
  )
}
