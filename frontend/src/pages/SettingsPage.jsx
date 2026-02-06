import React from 'react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

export function SettingsPage() {
  return (
    <div className="section-stack">
      <div className="page-header">
        <div>
          <h2>Settings</h2>
          <p>Workspace-level metadata and runtime defaults.</p>
        </div>
      </div>

      <div className="grid grid-2">
        <Card title="Environment" subtitle="Current application environment state.">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <span>Runtime</span>
            <Badge tone="success">Production-ready</Badge>
          </div>
          <div className="row" style={{ justifyContent: 'space-between', marginTop: 10 }}>
            <span>Policy Guardrails</span>
            <Badge tone="success">Enabled</Badge>
          </div>
          <div className="row" style={{ justifyContent: 'space-between', marginTop: 10 }}>
            <span>SQL Exposure</span>
            <Badge tone="neutral">Hidden in Chat</Badge>
          </div>
        </Card>

        <Card title="Guidance" subtitle="Recommended internal governance checks.">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            <li>Review role visibility weekly.</li>
            <li>Review denied-access audit events daily.</li>
            <li>Rotate database read-only credentials quarterly.</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
