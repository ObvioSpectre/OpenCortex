const baseKey = 'cortex_saved_insights'

function keyFor(userId, organizationId) {
  return `${baseKey}:${organizationId}:${userId}`
}

export function loadSavedInsights(userId, organizationId) {
  try {
    const raw = localStorage.getItem(keyFor(userId, organizationId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveInsight(userId, organizationId, insightEntry) {
  const existing = loadSavedInsights(userId, organizationId)
  const next = [insightEntry, ...existing].slice(0, 200)
  localStorage.setItem(keyFor(userId, organizationId), JSON.stringify(next))
  return next
}

export function deleteInsight(userId, organizationId, insightId) {
  const existing = loadSavedInsights(userId, organizationId)
  const next = existing.filter((x) => x.id !== insightId)
  localStorage.setItem(keyFor(userId, organizationId), JSON.stringify(next))
  return next
}

export function clearSavedInsights(userId, organizationId) {
  localStorage.removeItem(keyFor(userId, organizationId))
  return []
}
