import React, { useState } from 'react'
import { Card } from '../components/ui/Card'
import { DataTable } from '../components/ui/DataTable'
import { Button } from '../components/ui/Button'
import { api } from '../services/api'

export function AuditLogsPage() {
  const [organizationId, setOrganizationId] = useState('org_demo')
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('Ready')

  const load = async () => {
    try {
      const res = await api.listAuditLogs(organizationId)
      const data = (res.audit_logs || []).map((a) => ({
        id: a.id,
        user: a.user_id,
        role: a.role,
        timestamp: a.created_at,
        denied: a.access_denied ? 'Yes' : 'No',
        metrics: (a.metrics_accessed || []).join(', ') || '-',
        question: a.question,
      }))
      setRows(data)
      setStatus(`Loaded ${data.length} audit events.`)
    } catch (e) {
      setStatus(`Failed: ${e.message}`)
    }
  }

  return (
    <div className="section-stack">
      <div className="page-header">
        <div>
          <h2>Audit Logs</h2>
          <p>Trace who asked what, when, and whether access was denied.</p>
        </div>
      </div>

      <Card title="Audit Stream" subtitle="Operational transparency for governance teams.">
        <div className="row" style={{ marginBottom: 12 }}>
          <input className="input" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="Organization ID" />
          <Button onClick={load}>Load Audit Logs</Button>
        </div>
        <DataTable
          columns={[
            { key: 'timestamp', label: 'When' },
            { key: 'user', label: 'User' },
            { key: 'role', label: 'Role' },
            { key: 'question', label: 'Question' },
            { key: 'metrics', label: 'Metrics Accessed' },
            { key: 'denied', label: 'Denied' },
          ]}
          rows={rows}
        />
      </Card>

      <div className="status-bar">{status}</div>
    </div>
  )
}
