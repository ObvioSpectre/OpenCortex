import React, { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { AdminPage } from './pages/AdminPage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { ChatPage } from './pages/ChatPage'
import { SavedInsightsPage } from './pages/SavedInsightsPage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  const [page, setPage] = useState('admin')

  return (
    <AppShell active={page} onNavigate={setPage}>
      {page === 'admin' && <AdminPage />}
      {page === 'chat' && <ChatPage />}
      {page === 'saved' && <SavedInsightsPage />}
      {page === 'audit' && <AuditLogsPage />}
      {page === 'settings' && <SettingsPage />}
    </AppShell>
  )
}

export default App
