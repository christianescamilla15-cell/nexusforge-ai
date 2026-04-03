import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'
import StatusBadge from '../../shared/components/StatusBadge'

function formatDuration(ms) {
  if (!ms) return '--'
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  const d = new Date(iso)
  const locale = lang === 'es' ? 'es-ES' : 'en-US'
  return d.toLocaleString(locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function ExecutionListPage({ onSelectExecution, lang = 'en' }) {
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isDemo, setIsDemo] = useState(false)
  const [filter, setFilter] = useState('all')
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    fetchAPI('/executions').then((res) => {
      if (res.error) {
        setError(res.error)
      } else {
        // Normalize API shape → UI shape
        const raw = Array.isArray(res.data) ? res.data : (res.data?.runs || [])
        const runs = raw.map((r) => ({
          run_id: r.id || r.run_id,
          workflow_name: r.workflow_name || 'Workflow',
          status: r.status,
          started_at: r.started_at || r.created_at,
          duration_ms: r.total_latency_ms || r.latency_ms
            || (r.completed_at && r.started_at ? new Date(r.completed_at) - new Date(r.started_at) : null),
          total_cost: r.total_cost_usd || r.total_cost || r.cost || 0,
          steps_count: r.steps_count || r.agents_used?.length || 0,
        }))
        setExecutions(runs)
        setIsDemo(res.isDemo)
      }
      setLoading(false)
    })
  }, [])

  const FILTERS = [
    { key: 'all', label: t('all', lang) },
    { key: 'pending', label: t('pending', lang) },
    { key: 'running', label: t('running', lang) },
    { key: 'completed', label: t('completed', lang) },
    { key: 'failed', label: t('failed', lang) },
  ]

  const filtered = filter === 'all' ? executions : executions.filter((e) => e.status === filter)

  const tableHeaders = [t('status', lang), t('workflow', lang), t('start', lang), t('duration', lang), t('cost', lang), t('steps', lang)]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
            {t('executions', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {t('monitorExecutions', lang)}
            <span style={{ marginLeft: 8, color: '#6366F1' }}>{executions.length} {t('total', lang)}</span>
          </p>
        </div>
      </div>

      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
          Loading executions...
        </div>
      )}

      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
          color: '#991B1B', fontSize: 14,
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {isDemo && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 16,
          padding: '4px 12px', borderRadius: 6, fontSize: 12,
          background: 'rgba(245,158,11,0.08)', color: '#D97706',
          border: '1px solid rgba(245,158,11,0.2)', fontWeight: 600,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#D97706' }} />
          {lang === 'es' ? 'Modo Demo' : 'Demo Mode'}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            aria-label={`Filter: ${f.label}`}
            style={{
              padding: '6px 14px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 500,
              cursor: 'pointer', transition: 'all 0.15s',
              background: filter === f.key ? 'rgba(99,102,241,0.2)' : '#F3F4F6',
              color: filter === f.key ? '#818CF8' : '#9CA3AF',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div data-tour="execution-table" style={{
        background: '#FFFFFF', borderRadius: 12, border: '1px solid #E5E7EB',
        overflow: 'hidden', overflowX: 'auto',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? 600 : undefined }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
              {tableHeaders.map((h) => (
                <th key={h} style={{
                  padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                  {t('noExecutionsFilter', lang)}
                </td>
              </tr>
            )}
            {filtered.map((exec) => (
              <tr
                key={exec.run_id}
                onClick={() => onSelectExecution && onSelectExecution(exec.run_id)}
                style={{
                  borderBottom: '1px solid #F3F4F6',
                  cursor: 'pointer', transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#F3F4F6'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                aria-label={`${t('executions', lang)} ${exec.run_id}`}
              >
                <td style={{ padding: '12px 16px' }}><StatusBadge status={exec.status} /></td>
                <td style={{ padding: '12px 16px', color: '#111827', fontSize: 14, fontWeight: 500 }}>{exec.workflow_name}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13, whiteSpace: 'nowrap' }}>{formatDate(exec.started_at, lang)}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{formatDuration(exec.duration_ms)}</td>
                <td style={{ padding: '12px 16px', color: '#10B981', fontSize: 13, fontWeight: 500 }}>${exec.total_cost?.toFixed(3) || '0.000'}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{exec.steps_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
