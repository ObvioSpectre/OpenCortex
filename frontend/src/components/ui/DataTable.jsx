import React from 'react'

export function DataTable({ columns, rows, empty = 'No data available.' }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => <th key={c.key}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="muted">{empty}</td>
            </tr>
          )}
          {rows.map((row, i) => (
            <tr key={row.id || i}>
              {columns.map((c) => <td key={`${c.key}-${i}`}>{row[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
