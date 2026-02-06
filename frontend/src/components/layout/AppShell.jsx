import React from 'react'
import { Sidebar } from './Sidebar'

export function AppShell({ active, onNavigate, children }) {
  return (
    <div className="shell">
      <Sidebar active={active} onNavigate={onNavigate} />
      <main className="main">{children}</main>
    </div>
  )
}
