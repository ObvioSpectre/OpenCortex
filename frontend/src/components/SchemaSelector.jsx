import React from 'react'

export function SchemaSelector({ schema, selected, onToggle }) {
  if (!schema?.databases?.length) {
    return <p>No schema loaded.</p>
  }

  return (
    <div>
      {schema.databases.map((db) => (
        <div key={db.database_name} style={{ marginBottom: '1rem' }}>
          <h4>{db.database_name}</h4>
          {db.tables.map((table) => {
            const key = `${db.database_name}.${table.table_name}`
            const tableSelected = !!selected[key]
            return (
              <div key={key} style={{ border: '1px solid #ddd', padding: '0.75rem', marginBottom: '0.5rem' }}>
                <label>
                  <input
                    type="checkbox"
                    checked={tableSelected}
                    onChange={(e) => onToggle(db.database_name, table.table_name, null, e.target.checked)}
                  />
                  <strong style={{ marginLeft: '0.5rem' }}>{table.table_name}</strong>
                </label>
                {tableSelected && (
                  <div style={{ marginTop: '0.5rem', paddingLeft: '1rem' }}>
                    {table.columns.map((col) => {
                      const colSelected = selected[key]?.has(col.name)
                      return (
                        <label key={col.name} style={{ display: 'block' }}>
                          <input
                            type="checkbox"
                            checked={!!colSelected}
                            onChange={(e) => onToggle(db.database_name, table.table_name, col.name, e.target.checked)}
                          />
                          <span style={{ marginLeft: '0.5rem' }}>
                            {col.name} ({col.type})
                          </span>
                        </label>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
