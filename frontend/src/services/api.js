const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export const api = {
  createOrganization: (payload) => request('/admin/organizations', { method: 'POST', body: JSON.stringify(payload) }),
  createRole: (payload) => request('/admin/roles', { method: 'POST', body: JSON.stringify(payload) }),
  listRoles: (organizationId) => request(`/admin/organizations/${organizationId}/roles`),
  createUser: (payload) => request('/admin/users', { method: 'POST', body: JSON.stringify(payload) }),
  listUsers: (organizationId) => request(`/admin/organizations/${organizationId}/users`),
  listAuditLogs: (organizationId) => request(`/admin/organizations/${organizationId}/audit-logs`),

  connectDataSource: (payload) => request('/admin/data-sources/connect', { method: 'POST', body: JSON.stringify(payload) }),
  saveAllowlist: (payload) => request('/admin/allowlist', { method: 'POST', body: JSON.stringify(payload) }),
  buildSemantic: (dataSourceId) => request(`/admin/data-sources/${dataSourceId}/semantic/build`, { method: 'POST' }),
  getSemantic: (dataSourceId) => request(`/admin/data-sources/${dataSourceId}/semantic`),
  indexVectors: (dataSourceId) => request(`/admin/data-sources/${dataSourceId}/vector/index`, { method: 'POST' }),
  overrideSemanticVisibility: (dataSourceId, payload) => request(`/admin/data-sources/${dataSourceId}/semantic/visibility`, { method: 'POST', body: JSON.stringify(payload) }),

  ask: (payload) => request('/chat/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-user-id': payload.user_id,
      'x-organization-id': payload.organization_id,
      'x-role': payload.role,
    },
    body: JSON.stringify(payload),
  }),
}
