import React from 'react'

const NAV = [
  { key: 'admin', label: 'Admin' },
  { key: 'chat', label: 'Chat' },
  { key: 'saved', label: 'Saved Insights' },
  { key: 'audit', label: 'Audit Logs' },
  { key: 'settings', label: 'Settings' },
]

export function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" />
        <div>
          <h1>Cortex BI</h1>
          <span>Internal Console</span>
        </div>
      </div>

      <nav className="nav-list">
        {NAV.map((item) => (
          <button
            key={item.key}
            className={`nav-btn ${active === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
