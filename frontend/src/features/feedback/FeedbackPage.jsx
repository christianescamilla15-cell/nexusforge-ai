import { useState, useEffect, useCallback } from 'react'
import { t } from '../../shared/i18n/translations'
import { getMode, getApiUrl } from '../../services/api'

// ── Demo data (shown when API returns empty or in demo mode) ──
const DEMO_STATS = {
  total: 42,
  avg_rating: 4.1,
  approval_rate: 0.81,
  by_workflow: {
    'enterprise-ops': { total: 18, avg_rating: 4.3, approved: 16, approval_rate: 0.889 },
    'document-intelligence': { total: 14, avg_rating: 3.9, approved: 10, approval_rate: 0.714 },
    'portfolio-copilot': { total: 10, avg_rating: 4.0, approved: 8, approval_rate: 0.8 },
  },
}

const DEMO_AGENTS = [
  { agent_name: 'IntakeAgent', total_runs: 38, successful_runs: 36, failed_runs: 2, success_rate: 0.947, avg_quality_score: 0.86, avg_latency_ms: 120.4, retry_rate: 0.053, fallback_rate: 0.0, approval_rate: 0.84, operational_score: 0.891 },
  { agent_name: 'IntentClassifierAgent', total_runs: 38, successful_runs: 37, failed_runs: 1, success_rate: 0.974, avg_quality_score: 0.91, avg_latency_ms: 89.2, retry_rate: 0.026, fallback_rate: 0.0, approval_rate: 0.87, operational_score: 0.915 },
  { agent_name: 'DocumentRAGAgent', total_runs: 24, successful_runs: 22, failed_runs: 2, success_rate: 0.917, avg_quality_score: 0.83, avg_latency_ms: 245.8, retry_rate: 0.083, fallback_rate: 0.042, approval_rate: 0.75, operational_score: 0.821 },
  { agent_name: 'SupervisorAgent', total_runs: 38, successful_runs: 35, failed_runs: 3, success_rate: 0.921, avg_quality_score: 0.88, avg_latency_ms: 312.5, retry_rate: 0.105, fallback_rate: 0.026, approval_rate: 0.79, operational_score: 0.845 },
  { agent_name: 'SchedulerAgent', total_runs: 18, successful_runs: 17, failed_runs: 1, success_rate: 0.944, avg_quality_score: 0.85, avg_latency_ms: 156.3, retry_rate: 0.056, fallback_rate: 0.0, approval_rate: 0.83, operational_score: 0.872 },
  { agent_name: 'CRMUpdateAgent', total_runs: 18, successful_runs: 16, failed_runs: 2, success_rate: 0.889, avg_quality_score: 0.79, avg_latency_ms: 198.7, retry_rate: 0.111, fallback_rate: 0.056, approval_rate: 0.72, operational_score: 0.793 },
  { agent_name: 'NotificationAgent', total_runs: 18, successful_runs: 18, failed_runs: 0, success_rate: 1.0, avg_quality_score: 0.92, avg_latency_ms: 67.1, retry_rate: 0.0, fallback_rate: 0.0, approval_rate: 0.89, operational_score: 0.942 },
  { agent_name: 'CustomerContextAgent', total_runs: 18, successful_runs: 17, failed_runs: 1, success_rate: 0.944, avg_quality_score: 0.84, avg_latency_ms: 178.9, retry_rate: 0.056, fallback_rate: 0.0, approval_rate: 0.78, operational_score: 0.858 },
]

const DEMO_RECOMMENDATIONS = {
  status: 'ok',
  total_agents: 8,
  recommendations: [
    { agent: 'NotificationAgent', score: 0.942, status: 'excellent', success_rate: 1.0, avg_latency_ms: 67.1, suggestion: 'Keep NotificationAgent' },
    { agent: 'IntentClassifierAgent', score: 0.915, status: 'excellent', success_rate: 0.974, avg_latency_ms: 89.2, suggestion: 'Keep IntentClassifierAgent' },
    { agent: 'IntakeAgent', score: 0.891, status: 'excellent', success_rate: 0.947, avg_latency_ms: 120.4, suggestion: 'Keep IntakeAgent' },
    { agent: 'SchedulerAgent', score: 0.872, status: 'excellent', success_rate: 0.944, avg_latency_ms: 156.3, suggestion: 'Keep SchedulerAgent' },
    { agent: 'CustomerContextAgent', score: 0.858, status: 'excellent', success_rate: 0.944, avg_latency_ms: 178.9, suggestion: 'Keep CustomerContextAgent' },
    { agent: 'SupervisorAgent', score: 0.845, status: 'excellent', success_rate: 0.921, avg_latency_ms: 312.5, suggestion: 'Keep SupervisorAgent' },
    { agent: 'DocumentRAGAgent', score: 0.821, status: 'excellent', success_rate: 0.917, avg_latency_ms: 245.8, suggestion: 'Keep DocumentRAGAgent' },
    { agent: 'CRMUpdateAgent', score: 0.793, status: 'good', success_rate: 0.889, avg_latency_ms: 198.7, suggestion: 'Monitor CRMUpdateAgent' },
  ],
}

const DEMO_FEEDBACK_LIST = [
  { id: 'fb-1', run_id: 'run-abc-001', workflow_name: 'enterprise-ops', rating: 5, approved: true, feedback_type: 'human', comments: 'Fast and accurate response.', reviewer: 'christian', created_at: '2026-03-29T10:15:00Z' },
  { id: 'fb-2', run_id: 'run-abc-002', workflow_name: 'document-intelligence', rating: 4, approved: true, feedback_type: 'human', comments: 'Good extraction, minor formatting issue.', reviewer: 'christian', created_at: '2026-03-29T09:30:00Z' },
  { id: 'fb-3', run_id: 'run-abc-003', workflow_name: 'enterprise-ops', rating: 3, approved: false, feedback_type: 'human', comments: 'Missed the scheduling context.', reviewer: 'admin', created_at: '2026-03-28T16:45:00Z' },
  { id: 'fb-4', run_id: 'run-abc-004', workflow_name: 'portfolio-copilot', rating: 5, approved: true, feedback_type: 'auto', comments: 'Auto-approved: quality > 0.9', reviewer: 'system', created_at: '2026-03-28T14:20:00Z' },
  { id: 'fb-5', run_id: 'run-abc-005', workflow_name: 'document-intelligence', rating: 2, approved: false, feedback_type: 'human', comments: 'Failed to parse scanned document.', reviewer: 'christian', created_at: '2026-03-27T11:00:00Z' },
]

// ── Helpers ──
const isDarkTheme = () => document.documentElement.getAttribute('data-theme') === 'dark'

function StarRating({ value, onChange, readonly = false, size = 20 }) {
  const [hover, setHover] = useState(0)
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          onClick={() => !readonly && onChange && onChange(star)}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
          style={{
            cursor: readonly ? 'default' : 'pointer',
            fontSize: size,
            color: star <= (hover || value) ? '#F59E0B' : '#D1D5DB',
            transition: 'color 0.15s',
            userSelect: 'none',
          }}
        >
          &#9733;
        </span>
      ))}
    </div>
  )
}

function ScoreBadge({ score }) {
  const color = score >= 0.85 ? '#10B981' : score >= 0.7 ? '#F59E0B' : '#EF4444'
  const bg = score >= 0.85 ? 'rgba(16,185,129,0.1)' : score >= 0.7 ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 10px', borderRadius: 12, fontSize: 13, fontWeight: 600,
      color, background: bg, border: `1px solid ${color}22`,
    }}>
      {(score * 100).toFixed(1)}%
    </span>
  )
}

function StatusBadge({ status }) {
  const map = {
    excellent: { color: '#10B981', bg: 'rgba(16,185,129,0.1)', label: 'Excellent' },
    good: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', label: 'Good' },
    needs_improvement: { color: '#EF4444', bg: 'rgba(239,68,68,0.1)', label: 'Needs Review' },
  }
  const s = map[status] || map.good
  return (
    <span style={{
      padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
      color: s.color, background: s.bg, border: `1px solid ${s.color}22`,
    }}>
      {s.label}
    </span>
  )
}

// ── Main component ──
export default function FeedbackPage({ lang = 'en' }) {
  const dark = isDarkTheme()
  const [stats, setStats] = useState(DEMO_STATS)
  const [agents, setAgents] = useState(DEMO_AGENTS)
  const [recommendations, setRecommendations] = useState(DEMO_RECOMMENDATIONS)
  const [feedbackList, setFeedbackList] = useState(DEMO_FEEDBACK_LIST)
  const [tab, setTab] = useState('overview') // overview | agents | submit
  const [loading, setLoading] = useState(false)

  // Submit form state
  const [formRunId, setFormRunId] = useState('')
  const [formRating, setFormRating] = useState(3)
  const [formApproved, setFormApproved] = useState(false)
  const [formComments, setFormComments] = useState('')
  const [formReviewer, setFormReviewer] = useState('christian')
  const [submitStatus, setSubmitStatus] = useState(null)

  const isEn = lang === 'en'

  const fetchData = useCallback(async () => {
    if (getMode() === 'demo') return
    setLoading(true)
    try {
      const base = getApiUrl()
      const [statsRes, agentsRes, recsRes] = await Promise.all([
        fetch(`${base}/feedback/stats/`).then(r => r.json()).catch(() => null),
        fetch(`${base}/feedback/agents/performance/`).then(r => r.json()).catch(() => null),
        fetch(`${base}/feedback/agents/recommendations/`).then(r => r.json()).catch(() => null),
      ])
      if (statsRes && statsRes.total > 0) setStats(statsRes)
      if (agentsRes && agentsRes.agents && agentsRes.agents.length > 0) setAgents(agentsRes.agents)
      if (recsRes && recsRes.status === 'ok') setRecommendations(recsRes)
    } catch {
      // keep demo data
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleSubmit = async () => {
    if (!formRunId.trim()) return
    setSubmitStatus('submitting')
    try {
      const base = getApiUrl()
      const res = await fetch(`${base}/feedback/submit/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: formRunId,
          rating: formRating,
          approved: formApproved,
          comments: formComments,
          reviewer: formReviewer,
        }),
      })
      if (res.ok) {
        setSubmitStatus('success')
        setFormRunId('')
        setFormRating(3)
        setFormApproved(false)
        setFormComments('')
        fetchData()
      } else {
        setSubmitStatus('error')
      }
    } catch {
      setSubmitStatus('error')
    }
  }

  // ── Styles ──
  const card = {
    background: dark ? '#1A1B2E' : '#FFFFFF',
    border: `1px solid ${dark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
    borderRadius: 12,
    padding: 20,
  }
  const headerColor = dark ? '#E5E7EB' : '#111827'
  const mutedColor = dark ? '#9CA3AF' : '#6B7280'
  const accentColor = dark ? '#818CF8' : '#2563EB'

  const tabBtn = (key) => ({
    padding: '8px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
    fontWeight: tab === key ? 600 : 400, fontSize: 14,
    background: tab === key ? (dark ? 'rgba(99,102,241,0.15)' : 'rgba(37,99,235,0.08)') : 'transparent',
    color: tab === key ? accentColor : mutedColor,
    transition: 'all 0.15s',
  })

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: headerColor, margin: 0 }}>
          {isEn ? 'Feedback Loop' : 'Ciclo de Feedback'}
        </h1>
        <p style={{ color: mutedColor, fontSize: 14, margin: '4px 0 0' }}>
          {isEn
            ? 'Operational feedback, agent performance, and recommendations.'
            : 'Feedback operacional, rendimiento de agentes y recomendaciones.'}
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
        <button style={tabBtn('overview')} onClick={() => setTab('overview')}>
          {isEn ? 'Overview' : 'Resumen'}
        </button>
        <button style={tabBtn('agents')} onClick={() => setTab('agents')}>
          {isEn ? 'Agent Performance' : 'Rendimiento de Agentes'}
        </button>
        <button style={tabBtn('submit')} onClick={() => setTab('submit')}>
          {isEn ? 'Submit Feedback' : 'Enviar Feedback'}
        </button>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 40, color: mutedColor }}>
          {t('loading', lang)}
        </div>
      )}

      {/* ═══════ OVERVIEW TAB ═══════ */}
      {tab === 'overview' && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            {[
              { label: isEn ? 'Total Feedback' : 'Feedback Total', value: stats.total, icon: '#6366F1' },
              { label: isEn ? 'Avg Rating' : 'Rating Promedio', value: `${stats.avg_rating}/5`, icon: '#F59E0B' },
              { label: isEn ? 'Approval Rate' : 'Tasa de Aprobacion', value: `${(stats.approval_rate * 100).toFixed(1)}%`, icon: '#10B981' },
              { label: isEn ? 'Workflows Tracked' : 'Workflows Rastreados', value: Object.keys(stats.by_workflow).length, icon: '#8B5CF6' },
            ].map((kpi, i) => (
              <div key={i} style={card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: `${kpi.icon}18`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: kpi.icon }} />
                  </div>
                  <span style={{ fontSize: 13, color: mutedColor }}>{kpi.label}</span>
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: headerColor }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* Workflow breakdown */}
          <div style={card}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: headerColor, margin: '0 0 16px' }}>
              {isEn ? 'Feedback by Workflow' : 'Feedback por Workflow'}
            </h3>
            <div style={{ display: 'grid', gap: 12 }}>
              {Object.entries(stats.by_workflow).map(([wf, data]) => (
                <div key={wf} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 16px', borderRadius: 8,
                  background: dark ? 'rgba(255,255,255,0.03)' : '#F9FAFB',
                  border: `1px solid ${dark ? 'rgba(255,255,255,0.05)' : '#F3F4F6'}`,
                }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: headerColor }}>{wf}</div>
                    <div style={{ fontSize: 12, color: mutedColor, marginTop: 2 }}>
                      {data.total} {isEn ? 'reviews' : 'revisiones'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: mutedColor }}>{isEn ? 'Rating' : 'Rating'}</div>
                      <StarRating value={Math.round(data.avg_rating)} readonly size={14} />
                      <div style={{ fontSize: 11, color: mutedColor }}>{data.avg_rating}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: mutedColor }}>{isEn ? 'Approval' : 'Aprobacion'}</div>
                      <ScoreBadge score={data.approval_rate} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent feedback */}
          <div style={card}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: headerColor, margin: '0 0 16px' }}>
              {isEn ? 'Recent Feedback' : 'Feedback Reciente'}
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${dark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}` }}>
                    {[isEn ? 'Run ID' : 'ID Ejecucion', 'Workflow', isEn ? 'Rating' : 'Rating', isEn ? 'Approved' : 'Aprobado', isEn ? 'Type' : 'Tipo', isEn ? 'Comment' : 'Comentario'].map((h, i) => (
                      <th key={i} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: mutedColor, fontSize: 12 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {feedbackList.map((fb) => (
                    <tr key={fb.id} style={{ borderBottom: `1px solid ${dark ? 'rgba(255,255,255,0.04)' : '#F3F4F6'}` }}>
                      <td style={{ padding: '10px 12px', color: accentColor, fontFamily: 'monospace', fontSize: 12 }}>
                        {fb.run_id.slice(0, 12)}...
                      </td>
                      <td style={{ padding: '10px 12px', color: headerColor }}>{fb.workflow_name}</td>
                      <td style={{ padding: '10px 12px' }}><StarRating value={fb.rating} readonly size={14} /></td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                          color: fb.approved ? '#10B981' : '#EF4444',
                          background: fb.approved ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                        }}>
                          {fb.approved ? (isEn ? 'Yes' : 'Si') : 'No'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: mutedColor, fontSize: 12 }}>{fb.feedback_type}</td>
                      <td style={{ padding: '10px 12px', color: mutedColor, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {fb.comments || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recommendations */}
          <div style={card}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: headerColor, margin: '0 0 16px' }}>
              {isEn ? 'Agent Recommendations' : 'Recomendaciones de Agentes'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
              {recommendations.recommendations.slice(0, 6).map((rec) => (
                <div key={rec.agent} style={{
                  padding: '14px 16px', borderRadius: 10,
                  background: dark ? 'rgba(255,255,255,0.03)' : '#F9FAFB',
                  border: `1px solid ${dark ? 'rgba(255,255,255,0.05)' : '#F3F4F6'}`,
                  display: 'flex', flexDirection: 'column', gap: 8,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: headerColor }}>{rec.agent}</span>
                    <StatusBadge status={rec.status} />
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 12, color: mutedColor }}>
                    <span>{isEn ? 'Score' : 'Puntaje'}: <b style={{ color: headerColor }}>{(rec.score * 100).toFixed(1)}%</b></span>
                    <span>{isEn ? 'Success' : 'Exito'}: <b style={{ color: headerColor }}>{(rec.success_rate * 100).toFixed(1)}%</b></span>
                    <span>{isEn ? 'Latency' : 'Latencia'}: <b style={{ color: headerColor }}>{rec.avg_latency_ms.toFixed(0)}ms</b></span>
                  </div>
                  <div style={{ fontSize: 12, color: accentColor, fontStyle: 'italic' }}>{rec.suggestion}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══════ AGENTS TAB ═══════ */}
      {tab === 'agents' && !loading && (
        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: headerColor, margin: '0 0 16px' }}>
            {isEn ? 'Agent Performance Leaderboard' : 'Tabla de Rendimiento de Agentes'}
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${dark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'}` }}>
                  {[
                    '#',
                    isEn ? 'Agent' : 'Agente',
                    isEn ? 'Runs' : 'Ejecuciones',
                    isEn ? 'Success Rate' : 'Tasa Exito',
                    isEn ? 'Quality' : 'Calidad',
                    isEn ? 'Latency' : 'Latencia',
                    isEn ? 'Retry Rate' : 'Tasa Retry',
                    isEn ? 'Approval' : 'Aprobacion',
                    isEn ? 'Op. Score' : 'Puntaje Op.',
                  ].map((h, i) => (
                    <th key={i} style={{
                      padding: '10px 12px', textAlign: i === 0 ? 'center' : 'left',
                      fontWeight: 600, color: mutedColor, fontSize: 12, whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...agents].sort((a, b) => b.operational_score - a.operational_score).map((agent, idx) => (
                  <tr key={agent.agent_name} style={{
                    borderBottom: `1px solid ${dark ? 'rgba(255,255,255,0.04)' : '#F3F4F6'}`,
                    background: idx < 3 ? (dark ? 'rgba(99,102,241,0.04)' : 'rgba(37,99,235,0.02)') : 'transparent',
                  }}>
                    <td style={{ padding: '12px', textAlign: 'center', fontWeight: 700, color: idx < 3 ? accentColor : mutedColor }}>
                      {idx + 1}
                    </td>
                    <td style={{ padding: '12px', fontWeight: 600, color: headerColor }}>{agent.agent_name}</td>
                    <td style={{ padding: '12px', color: headerColor }}>
                      {agent.total_runs}
                      <span style={{ fontSize: 11, color: mutedColor, marginLeft: 4 }}>
                        ({agent.successful_runs}/{agent.failed_runs})
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}><ScoreBadge score={agent.success_rate} /></td>
                    <td style={{ padding: '12px' }}><ScoreBadge score={agent.avg_quality_score} /></td>
                    <td style={{ padding: '12px', color: headerColor, fontFamily: 'monospace', fontSize: 12 }}>
                      {agent.avg_latency_ms.toFixed(0)}ms
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        color: agent.retry_rate > 0.1 ? '#EF4444' : agent.retry_rate > 0.05 ? '#F59E0B' : '#10B981',
                        fontWeight: 600, fontSize: 12,
                      }}>
                        {(agent.retry_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}><ScoreBadge score={agent.approval_rate} /></td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 60, height: 6, borderRadius: 3,
                          background: dark ? 'rgba(255,255,255,0.1)' : '#E5E7EB',
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%', borderRadius: 3,
                            width: `${agent.operational_score * 100}%`,
                            background: agent.operational_score >= 0.85 ? '#10B981' : agent.operational_score >= 0.7 ? '#F59E0B' : '#EF4444',
                            transition: 'width 0.5s ease',
                          }} />
                        </div>
                        <span style={{ fontWeight: 700, fontSize: 13, color: headerColor, minWidth: 48 }}>
                          {(agent.operational_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ═══════ SUBMIT TAB ═══════ */}
      {tab === 'submit' && !loading && (
        <div style={{ ...card, maxWidth: 600 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: headerColor, margin: '0 0 20px' }}>
            {isEn ? 'Submit Run Feedback' : 'Enviar Feedback de Ejecucion'}
          </h3>

          {/* Run ID */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: headerColor, marginBottom: 6 }}>
              Run ID
            </label>
            <input
              type="text"
              value={formRunId}
              onChange={(e) => setFormRunId(e.target.value)}
              placeholder="run-abc-001"
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                border: `1px solid ${dark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'}`,
                background: dark ? '#0F1117' : '#F9FAFB', color: headerColor,
                outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Rating */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: headerColor, marginBottom: 6 }}>
              {isEn ? 'Rating' : 'Calificacion'}
            </label>
            <StarRating value={formRating} onChange={setFormRating} size={28} />
          </div>

          {/* Approved */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formApproved}
                onChange={(e) => setFormApproved(e.target.checked)}
                style={{ width: 18, height: 18, accentColor: accentColor }}
              />
              <span style={{ fontSize: 14, fontWeight: 600, color: headerColor }}>
                {isEn ? 'Approve this run' : 'Aprobar esta ejecucion'}
              </span>
            </label>
          </div>

          {/* Comments */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: headerColor, marginBottom: 6 }}>
              {isEn ? 'Comments' : 'Comentarios'}
            </label>
            <textarea
              value={formComments}
              onChange={(e) => setFormComments(e.target.value)}
              rows={3}
              placeholder={isEn ? 'Optional comments...' : 'Comentarios opcionales...'}
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                border: `1px solid ${dark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'}`,
                background: dark ? '#0F1117' : '#F9FAFB', color: headerColor,
                outline: 'none', resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Reviewer */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: headerColor, marginBottom: 6 }}>
              {isEn ? 'Reviewer' : 'Revisor'}
            </label>
            <input
              type="text"
              value={formReviewer}
              onChange={(e) => setFormReviewer(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                border: `1px solid ${dark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'}`,
                background: dark ? '#0F1117' : '#F9FAFB', color: headerColor,
                outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!formRunId.trim() || submitStatus === 'submitting'}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: accentColor, color: '#fff', fontWeight: 600, fontSize: 14,
              cursor: formRunId.trim() ? 'pointer' : 'not-allowed',
              opacity: formRunId.trim() ? 1 : 0.5,
              transition: 'opacity 0.15s',
            }}
          >
            {submitStatus === 'submitting'
              ? (isEn ? 'Submitting...' : 'Enviando...')
              : (isEn ? 'Submit Feedback' : 'Enviar Feedback')}
          </button>

          {submitStatus === 'success' && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(16,185,129,0.1)', color: '#10B981', fontSize: 13, fontWeight: 600 }}>
              {isEn ? 'Feedback submitted successfully!' : 'Feedback enviado exitosamente!'}
            </div>
          )}
          {submitStatus === 'error' && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(239,68,68,0.1)', color: '#EF4444', fontSize: 13, fontWeight: 600 }}>
              {isEn ? 'Error submitting feedback. Try again.' : 'Error al enviar feedback. Intenta de nuevo.'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
