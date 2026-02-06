import React, { useMemo, useState } from 'react'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { clearSavedInsights, deleteInsight, loadSavedInsights } from '../services/savedInsights'

function toDisplayDate(iso) {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export function SavedInsightsPage() {
  const [organizationId, setOrganizationId] = useState('org_demo')
  const [userId, setUserId] = useState('alice')
  const [entries, setEntries] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [status, setStatus] = useState('Load saved insights for a user to begin.')

  const selected = useMemo(() => entries.find((e) => e.id === selectedId) || null, [entries, selectedId])

  const load = () => {
    const rows = loadSavedInsights(userId, organizationId)
    setEntries(rows)
    setSelectedId(rows[0]?.id || null)
    setStatus(`Loaded ${rows.length} saved insight${rows.length === 1 ? '' : 's'}.`)
  }

  const remove = (id) => {
    const next = deleteInsight(userId, organizationId, id)
    setEntries(next)
    setSelectedId(next[0]?.id || null)
    setStatus('Saved insight deleted.')
  }

  const clearAll = () => {
    clearSavedInsights(userId, organizationId)
    setEntries([])
    setSelectedId(null)
    setStatus('All saved insights cleared.')
  }

  return (
    <div className="section-stack">
      <div className="page-header">
        <div>
          <h2>Saved Insights</h2>
          <p>Your curated executive briefings, saved for recurring decision cycles.</p>
        </div>
      </div>

      <Card title="Insight Library" subtitle="Stored per user and organization in the current workspace browser.">
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr auto auto', marginBottom: 14 }}>
          <input className="input" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="Organization ID" />
          <input className="input" value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="User ID" />
          <Button onClick={load}>Load</Button>
          <Button variant="ghost" onClick={clearAll}>Clear All</Button>
        </div>

        <div className="grid grid-2">
          <div className="section-stack">
            {entries.length === 0 && <p className="muted">No saved insights yet.</p>}
            {entries.map((entry) => (
              <button
                key={entry.id}
                className="card"
                style={{ textAlign: 'left', cursor: 'pointer', boxShadow: 'none', borderColor: selectedId === entry.id ? '#9cb0df' : undefined }}
                onClick={() => setSelectedId(entry.id)}
              >
                <div className="card-head" style={{ marginBottom: 8 }}>
                  <strong style={{ fontSize: 14 }}>{entry.question}</strong>
                  <Badge tone={entry.confidence === 'High' ? 'success' : 'warning'}>{entry.confidence}</Badge>
                </div>
                <p className="muted" style={{ margin: 0 }}>{toDisplayDate(entry.created_at)}</p>
              </button>
            ))}
          </div>

          <Card title="Insight Detail" subtitle="Review and share with leadership.">
            {!selected && <p className="muted">Select a saved insight from the left panel.</p>}
            {selected && (
              <div className="insight-grid">
                <p style={{ margin: 0 }}><strong>Question:</strong> {selected.question}</p>
                <p style={{ margin: 0 }}><strong>Summary:</strong> {selected.insight.executive_summary}</p>
                <div>
                  <strong>Key Insights</strong>
                  <ul>
                    {selected.insight.key_insights.map((line, idx) => <li key={idx}>{line}</li>)}
                  </ul>
                </div>
                <div>
                  <strong>Recommendations</strong>
                  <ul>
                    {selected.insight.recommendations.map((line, idx) => <li key={idx}>{line}</li>)}
                  </ul>
                </div>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <Badge tone={selected.confidence === 'High' ? 'success' : 'warning'}>{selected.confidence} Confidence</Badge>
                  <Button variant="ghost" onClick={() => remove(selected.id)}>Delete</Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </Card>

      <div className="status-bar">{status}</div>
    </div>
  )
}
