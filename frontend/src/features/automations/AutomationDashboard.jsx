import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import StatusBadge from '../../shared/components/StatusBadge'
import { CopyButton } from '../../shared/hooks/useCopyClipboard.jsx'
import RulesPanel from '../rules/RulesPanel'
import VariablesPanel from '../variables/VariablesPanel'
import AuditLog from '../audit/AuditLog'

function formatDuration(ms) {
  if (!ms) return '--'
  if (ms < 1000) return `${ms}ms`
  const s = Math.floor(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

// Inline SVG bar chart — last 10 runs by day
function RunsChart({ runs, color = '#6366F1' }) {
  if (!runs || runs.length === 0) return null

  // Group by day
  const byDay = {}
  runs.forEach(r => {
    const day = r.created_at?.slice(0, 10) || 'unknown'
    byDay[day] = (byDay[day] || 0) + 1
  })
  const days = Object.entries(byDay).slice(-7)
  const max = Math.max(...days.map(([, v]) => v), 1)
  const W = 280, H = 60, barW = Math.floor(W / days.length) - 4

  return (
    <svg width={W} height={H} style={{ display: 'block' }}>
      {days.map(([day, count], i) => {
        const barH = Math.max(4, Math.round((count / max) * (H - 16)))
        const x = i * (barW + 4)
        const y = H - barH - 8
        return (
          <g key={day}>
            <rect x={x} y={y} width={barW} height={barH} rx={3}
              fill={color} opacity={0.8} />
            <text x={x + barW / 2} y={H - 1} textAnchor="middle"
              fontSize={8} fill="#9CA3AF">
              {day.slice(5)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

const TABS = [
  { key: 'stats', en: 'Stats', es: 'Estadísticas' },
  { key: 'variables', en: 'Variables', es: 'Variables' },
  { key: 'rules', en: 'Rules', es: 'Reglas' },
  { key: 'audit', en: 'Audit', es: 'Auditoría' },
]

export default function AutomationDashboard({ automationId, onBack, onRun, lang = 'en' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('stats')

  useEffect(() => {
    if (!automationId) return
    setLoading(true)
    fetchAPI(`/automations/${automationId}/dashboard`).then(res => {
      if (res.error) setError(res.error)
      else setData(res.data)
      setLoading(false)
    })
  }, [automationId])

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF' }}>
      {lang === 'es' ? 'Cargando dashboard...' : 'Loading dashboard...'}
    </div>
  )

  if (error) return (
    <div style={{ padding: 24, color: '#DC2626', fontSize: 13 }}>Error: {error}</div>
  )

  if (!data) return null

  const { automation: auto, stats, recent_runs } = data
  const color = auto.color || '#6366F1'
  const bg = `${color}12`

  const apiBase = typeof window !== 'undefined'
    ? (localStorage.getItem('nexusforge_api_url') || 'https://nexusforge-api.onrender.com/api')
    : ''
  const webhookUrl = auto.webhook_secret ? `${apiBase}/automations/webhook/${auto.webhook_secret}` : null

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={onBack} style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8, width: 36, height: 36,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>
          {auto.icon}
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#111827', margin: 0 }}>{auto.name}</h1>
          <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>{auto.description || auto.workflow_name}</p>
        </div>
        <button onClick={() => onRun && onRun(auto)} style={{
          padding: '9px 18px', borderRadius: 9, border: 'none', fontSize: 13, fontWeight: 600,
          background: `linear-gradient(135deg, ${color}, ${color})`, color: '#fff', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>▶</span> {lang === 'es' ? 'Ejecutar' : 'Run'}
        </button>
      </div>

      {/* Stats cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: lang === 'es' ? 'Total ejecuciones' : 'Total runs', value: stats.total_runs, color: '#6366F1' },
          { label: lang === 'es' ? 'Tasa de éxito' : 'Success rate', value: `${stats.success_rate}%`, color: '#10B981' },
          { label: lang === 'es' ? 'Duración prom.' : 'Avg duration', value: formatDuration(stats.avg_duration_ms), color: '#F59E0B' },
          { label: lang === 'es' ? 'Costo total' : 'Total cost', value: `$${stats.total_cost.toFixed(4)}`, color: '#8B5CF6' },
        ].map(s => (
          <div key={s.label} style={{
            padding: '14px 16px', borderRadius: 10,
            background: `${s.color}0d`, border: `1px solid ${s.color}22`,
          }}>
            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 0, marginBottom: 20,
        borderBottom: '2px solid #E5E7EB',
      }}>
        {TABS.map(tab => {
          const active = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: '10px 20px', fontSize: 13, fontWeight: active ? 700 : 500,
                color: active ? color : '#6B7280',
                background: 'none', border: 'none', cursor: 'pointer',
                borderBottom: active ? `2px solid ${color}` : '2px solid transparent',
                marginBottom: -2, transition: 'all 0.15s',
              }}
            >
              {lang === 'es' ? tab.es : tab.en}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'stats' && (
        <>
          {/* Chart + webhook URL */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 280, background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 12 }}>
                {lang === 'es' ? 'Ejecuciones por día' : 'Runs per day'}
              </p>
              <RunsChart runs={recent_runs} color={color} />
            </div>

            {webhookUrl && (
              <div style={{ flex: 1, minWidth: 280, background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>
                  Webhook URL
                </p>
                <div style={{
                  padding: '8px 12px', borderRadius: 8, background: '#F9FAFB',
                  border: '1px solid #E5E7EB', fontSize: 11, fontFamily: 'monospace',
                  color: '#374151', wordBreak: 'break-all', marginBottom: 8,
                }}>
                  {webhookUrl}
                </div>
                <CopyButton text={webhookUrl} lang={lang} />
              </div>
            )}
          </div>

          {/* Recent runs table */}
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #F3F4F6' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
                {lang === 'es' ? 'Ejecuciones recientes' : 'Recent runs'}
              </h3>
            </div>
            {recent_runs.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
                {lang === 'es' ? 'Sin ejecuciones aún.' : 'No runs yet.'}
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
                    {[
                      lang === 'es' ? 'Estado' : 'Status',
                      lang === 'es' ? 'Inicio' : 'Started',
                      lang === 'es' ? 'Duración' : 'Duration',
                      'Tokens',
                      lang === 'es' ? 'Costo' : 'Cost',
                    ].map((h, i) => (
                      <th key={i} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recent_runs.map(r => (
                    <tr key={r.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '10px 16px' }}><StatusBadge status={r.status} /></td>
                      <td style={{ padding: '10px 16px', color: '#6B7280' }}>{formatDate(r.started_at, lang)}</td>
                      <td style={{ padding: '10px 16px', color: '#6B7280' }}>{formatDuration(r.duration_ms)}</td>
                      <td style={{ padding: '10px 16px', color: '#6B7280' }}>{r.total_tokens || '--'}</td>
                      <td style={{ padding: '10px 16px', color: '#10B981', fontWeight: 500 }}>${r.total_cost_usd?.toFixed(5) || '0.00000'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {activeTab === 'variables' && (
        <VariablesPanel automationId={automationId} lang={lang} />
      )}

      {activeTab === 'rules' && (
        <RulesPanel automationId={automationId} lang={lang} />
      )}

      {activeTab === 'audit' && (
        <AuditLog entityType="automation" entityId={automationId} lang={lang} />
      )}
    </div>
  )
}
