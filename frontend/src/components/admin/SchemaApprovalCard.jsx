import React from 'react'
import { Card } from '../ui/Card'
import { Toggle } from '../ui/Toggle'

export function SchemaApprovalCard({ schema, selected, onToggle }) {
  const databases = schema?.databases || []

  return (
    <Card title="Approve Tables & Columns" subtitle="Select only business-approved schema objects.">
      {databases.length === 0 && <p className="muted">Load schema after connecting database.</p>}
      <div className="section-stack">
        {databases.map((db) => (
          <div key={db.database_name} className="card" style={{ padding: 12, boxShadow: 'none' }}>
            <h4 style={{ margin: '0 0 10px' }}>{db.database_name}</h4>
            <div className="section-stack">
              {db.tables.map((table) => {
                const key = `${db.database_name}.${table.table_name}`
                const tableSelected = !!selected[key]
                return (
                  <div key={key} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 10 }}>
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                      <strong>{table.table_name}</strong>
                      <Toggle checked={tableSelected} onChange={(checked) => onToggle(db.database_name, table.table_name, null, checked)} />
                    </div>
                    {tableSelected && (
                      <div className="pill-wrap" style={{ marginTop: 10 }}>
                        {table.columns.map((col) => {
                          const checked = selected[key]?.has(col.name)
                          return (
                            <button
                              key={col.name}
                              className="pill"
                              onClick={() => onToggle(db.database_name, table.table_name, col.name, !checked)}
                              style={{
                                cursor: 'pointer',
                                background: checked ? '#e7eefc' : undefined,
                                borderColor: checked ? '#9eb1de' : undefined,
                              }}
                            >
                              {col.name}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
