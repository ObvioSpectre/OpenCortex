import React, { useEffect, useMemo, useState } from 'react'
import { InsightResponse } from '../components/chat/InsightResponse'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { api } from '../services/api'
import { saveInsight } from '../services/savedInsights'

const FALLBACK_SUGGESTIONS = {
  executive: [
    'What is the overall business trend in the last 6 months?',
    'Where are we underperforming and what should we do next?',
  ],
  finance: [
    'How has revenue changed over the last 6 months?',
    'What are the biggest financial risks this quarter?',
  ],
  sales: [
    'What is the units sold trend in the last 6 months?',
    'Which region needs sales intervention right now?',
  ],
}

function normalizeMetricName(metricName) {
  return metricName
    .replace(/_count_distinct|_count|_sum/g, '')
    .replace(/_/g, ' ')
    .trim()
}

function toUnique(items) {
  return Array.from(new Set(items))
}

function buildSuggestedQuestions(visibleMetrics, role) {
  const phrases = toUnique(visibleMetrics.map((m) => normalizeMetricName(m.name)).filter(Boolean)).slice(0, 4)
  const suggestions = []

  for (const phrase of phrases) {
    suggestions.push(`What is the ${phrase} trend over the last 6 months?`)
    suggestions.push(`How did ${phrase} change versus the previous period?`)
    suggestions.push(`What should we do to improve ${phrase}?`)
  }

  if (suggestions.length === 0) {
    return FALLBACK_SUGGESTIONS[role] || FALLBACK_SUGGESTIONS.executive
  }

  return suggestions.slice(0, 6)
}

function extractTimeRange(question, prev) {
  const q = question.toLowerCase()
  const relative = q.match(/last\s+\d+\s+(day|days|week|weeks|month|months|year|years)/)
  if (relative) return relative[0]
  if (q.includes('this quarter')) return 'this quarter'
  if (q.includes('this month')) return 'this month'
  if (q.includes('this year')) return 'this year'
  return prev || null
}

function extractMetric(question, metricPhrases, prev) {
  const q = question.toLowerCase()
  for (const phrase of metricPhrases) {
    if (q.includes(phrase.toLowerCase())) return phrase
  }
  return prev || null
}

function isFollowUpQuestion(question) {
  const q = question.trim().toLowerCase()
  if (!q) return false
  return (
    q.startsWith('compare') ||
    q.startsWith('break down') ||
    q.startsWith('what about') ||
    q.startsWith('and ') ||
    q.includes('same metric') ||
    q.includes('previous period') ||
    q.includes('this trend') ||
    q.includes('that trend') ||
    q.includes('drill down')
  )
}

function composeQuestionWithContext(rawQuestion, context, force = false) {
  if (!force && !isFollowUpQuestion(rawQuestion)) return rawQuestion
  const contextParts = []
  if (context.metric) contextParts.push(`metric: ${context.metric}`)
  if (context.timeRange) contextParts.push(`time range: ${context.timeRange}`)
  if (!contextParts.length) return rawQuestion
  return `${rawQuestion} (Use previous context: ${contextParts.join('; ')})`
}

function deriveConfidence(response) {
  const rows = response?.rows || []
  const limitations = response?.insight?.limitations
  if (limitations) return 'Medium'
  if (rows.length < 2) return 'Medium'

  const complete = rows.every((row) => {
    if (!row || typeof row !== 'object') return false
    const vals = Object.values(row)
    return vals.length > 0 && vals.every((v) => v !== null && v !== undefined)
  })

  return complete ? 'High' : 'Medium'
}

function buildFollowUpChips(context) {
  return [
    `Compare this against the previous period`,
    `Break this down by region`,
    `What are the top drivers behind this trend?`,
    `What actions should leadership take in the next 30 days?`,
    context.metric ? `How can we improve ${context.metric}?` : 'How can we improve this metric?',
  ]
}

export function ChatPage() {
  const [userId, setUserId] = useState('alice')
  const [organizationId, setOrganizationId] = useState('org_demo')
  const [role, setRole] = useState('executive')
  const [dataSourceId, setDataSourceId] = useState('default_mysql')
  const [question, setQuestion] = useState('What is the sales trend over the last 5 months and what should we do?')

  const [messages, setMessages] = useState([])
  const [latestInsight, setLatestInsight] = useState(null)
  const [latestRows, setLatestRows] = useState([])
  const [lastQuestion, setLastQuestion] = useState('')
  const [confidence, setConfidence] = useState('Medium')
  const [status, setStatus] = useState('Ready')

  const [metricCatalog, setMetricCatalog] = useState([])
  const [suggestedQuestions, setSuggestedQuestions] = useState([])
  const [followUpChips, setFollowUpChips] = useState([])
  const [context, setContext] = useState({ metric: null, timeRange: null })

  const metricPhrases = useMemo(
    () => toUnique(metricCatalog.map((m) => normalizeMetricName(m.name)).filter(Boolean)),
    [metricCatalog],
  )

  useEffect(() => {
    let active = true

    const loadSuggestions = async () => {
      try {
        const semantic = await api.getSemantic(dataSourceId)
        const visibleMetrics = (semantic.metrics || []).filter((m) => {
          const roles = m.allowed_roles || []
          return roles.length === 0 || roles.includes(role)
        })

        if (!active) return
        setMetricCatalog(visibleMetrics)
        setSuggestedQuestions(buildSuggestedQuestions(visibleMetrics, role))
      } catch {
        if (!active) return
        setMetricCatalog([])
        setSuggestedQuestions(FALLBACK_SUGGESTIONS[role] || FALLBACK_SUGGESTIONS.executive)
      }
    }

    loadSuggestions()
    return () => {
      active = false
    }
  }, [dataSourceId, role])

  const ask = async (candidateQuestion, options = {}) => {
    const rawQuestion = (candidateQuestion ?? question).trim()
    if (!rawQuestion) return

    const finalQuestion = composeQuestionWithContext(rawQuestion, context, options.forceFollowUp === true)

    setMessages((prev) => [...prev, { role: 'user', content: rawQuestion }])
    setStatus('Analyzing...')

    try {
      const res = await api.ask({
        user_id: userId,
        organization_id: organizationId,
        role,
        data_source_id: dataSourceId,
        question: finalQuestion,
        show_sql: false,
      })

      const summary = res?.insight?.executive_summary || 'Response received.'
      setMessages((prev) => [...prev, { role: 'assistant', content: summary }])

      const nextContext = {
        metric: extractMetric(rawQuestion, metricPhrases, context.metric),
        timeRange: extractTimeRange(rawQuestion, context.timeRange),
      }

      setContext(nextContext)
      setFollowUpChips(buildFollowUpChips(nextContext))
      setLatestInsight(res.insight)
      setLatestRows(res.rows || [])
      setLastQuestion(rawQuestion)
      setConfidence(deriveConfidence(res))
      setStatus('Answer ready.')

      if (!options.keepQuestion) {
        setQuestion('')
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'I cannot complete that request right now.' }])
      setStatus(`Failed: ${e.message}`)
    }
  }

  const saveCurrentInsight = () => {
    if (!latestInsight) return

    const entry = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      created_at: new Date().toISOString(),
      user_id: userId,
      organization_id: organizationId,
      role,
      data_source_id: dataSourceId,
      question: lastQuestion,
      confidence,
      context,
      insight: latestInsight,
    }

    saveInsight(userId, organizationId, entry)
    setStatus('Insight saved to your personal library.')
  }

  return (
    <div className="section-stack">
      <div className="page-header">
        <div>
          <h2>Leader Chat</h2>
          <p>Daily executive assistant for decisions, trends, and next actions.</p>
        </div>
      </div>

      <Card title="Session Context" subtitle="Workspace identity for secure data routing.">
        <div className="grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <input className="input" value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="User ID" />
          <input className="input" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="Organization ID" />
          <input className="input" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role" />
          <input className="input" value={dataSourceId} onChange={(e) => setDataSourceId(e.target.value)} placeholder="Data source ID" />
        </div>
      </Card>

      <Card title="Suggested Questions" subtitle="Role-aware prompts based on visible metrics.">
        <div className="chip-row">
          {suggestedQuestions.map((q, idx) => (
            <button key={`${q}-${idx}`} className="chip" onClick={() => ask(q, { forceFollowUp: false })}>
              {q}
            </button>
          ))}
        </div>
      </Card>

      <div className="chat-shell">
        <div className="chat-messages">
          {messages.length === 0 && <p className="muted">Ask a question or use suggested prompts for faster insights.</p>}
          {messages.map((msg, idx) => (
            <div key={idx} className={`msg ${msg.role}`}>
              {msg.content}
            </div>
          ))}
        </div>
        <div className="chat-input">
          <textarea
            className="textarea"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask in plain English: What is the sales trend over the last 5 months?"
          />
          <Button onClick={() => ask()}>Send</Button>
        </div>
      </div>

      <InsightResponse
        insight={latestInsight}
        rows={latestRows}
        confidence={confidence}
        onSaveInsight={saveCurrentInsight}
      />

      {latestInsight && (
        <Card title="Follow-up Questions" subtitle="Continue the conversation with preserved context.">
          <div className="chip-row">
            {followUpChips.map((chip, idx) => (
              <button key={`${chip}-${idx}`} className="chip" onClick={() => ask(chip, { forceFollowUp: true })}>
                {chip}
              </button>
            ))}
          </div>
        </Card>
      )}

      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div className="status-bar">{status}</div>
        <Badge tone={confidence === 'High' ? 'success' : 'warning'}>{confidence} Confidence</Badge>
      </div>
    </div>
  )
}
