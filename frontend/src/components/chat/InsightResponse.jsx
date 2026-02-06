import React from 'react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'

function renderKpis(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return null
  const first = rows[0]
  const kpis = Object.entries(first)
    .filter(([_, value]) => typeof value === 'number')
    .slice(0, 3)

  if (!kpis.length) return null

  return (
    <div className="kpi-row">
      {kpis.map(([key, value]) => (
        <div key={key} className="kpi-box">
          <span>{key.replace(/_/g, ' ')}</span>
          <strong>{Number(value).toLocaleString()}</strong>
        </div>
      ))}
    </div>
  )
}

export function InsightResponse({ insight, confidence = 'Medium', rows = [], onSaveInsight }) {
  if (!insight) return null

  return (
    <Card
      title="Executive Brief"
      subtitle="Auto-generated from live approved data."
      right={
        <div className="row">
          <Badge tone={confidence === 'High' ? 'success' : 'warning'}>{confidence} Confidence</Badge>
          <Button variant="secondary" onClick={onSaveInsight}>Save Insight</Button>
        </div>
      }
    >
      <div className="insight-grid">
        {renderKpis(rows)}
        <div>
          <strong>Summary</strong>
          <p style={{ margin: '6px 0 0' }}>{insight.executive_summary}</p>
        </div>
        <div>
          <strong>Key Insights</strong>
          <ul>
            {insight.key_insights.map((line, idx) => <li key={idx}>{line}</li>)}
          </ul>
        </div>
        <div>
          <strong>Recommendations</strong>
          <ul>
            {insight.recommendations.map((line, idx) => <li key={idx}>{line}</li>)}
          </ul>
        </div>
        {insight.limitations && (
          <div>
            <strong>Limitations</strong>
            <p style={{ margin: '6px 0 0' }}>{insight.limitations}</p>
          </div>
        )}
      </div>
    </Card>
  )
}
