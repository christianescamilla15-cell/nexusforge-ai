import { useState, useEffect, useRef } from 'react'
import { api } from '../../api/client'
import { t } from '../../shared/i18n/translations'
import StatusBadge from '../../shared/components/StatusBadge'

const DEMO_EXECUTIONS = [
  { run_id: 'run-001', workflow_name: 'Clasificar Documentos', status: 'completed', started_at: '2026-03-26T09:12:00Z', duration_ms: 14200, total_cost: 0.032, steps_count: 4 },
  { run_id: 'run-002', workflow_name: 'Extraer Datos Financieros', status: 'running', started_at: '2026-03-26T10:05:00Z', duration_ms: null, total_cost: 0.018, steps_count: 6 },
  { run_id: 'run-003', workflow_name: 'Resumir Contratos', status: 'failed', started_at: '2026-03-26T08:30:00Z', duration_ms: 5400, total_cost: 0.009, steps_count: 3 },
  { run_id: 'run-004', workflow_name: 'Analizar Sentimiento', status: 'completed', started_at: '2026-03-25T17:45:00Z', duration_ms: 8700, total_cost: 0.021, steps_count: 5 },
  { run_id: 'run-005', workflow_name: 'Pipeline RAG Completo', status: 'pending', started_at: '2026-03-26T10:10:00Z', duration_ms: null, total_cost: 0, steps_count: 8 },
  { run_id: 'run-006', workflow_name: 'Generar Reporte', status: 'completed', started_at: '2026-03-25T14:22:00Z', duration_ms: 22100, total_cost: 0.047, steps_count: 7 },
  { run_id: 'run-007', workflow_name: 'Clasificar Documentos', status: 'cancelled', started_at: '2026-03-25T11:00:00Z', duration_ms: 3200, total_cost: 0.004, steps_count: 2 },
]

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
  const [filter, setFilter] = useState('all')
  const [isMobile, setIsMobile] = useState(false)
  const intervalRef = useRef(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const fetchExecutions = async () => {
    try {
      const data = await api.get('/executions')
      setExecutions(Array.isArray(data) ? data : data.items || DEMO_EXECUTIONS)
    } catch {
      setExecutions(DEMO_EXECUTIONS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchExecutions()
    intervalRef.current = setInterval(fetchExecutions, 5000)
    return () => clearInterval(intervalRef.current)
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

  if (loading) {
    return (
      <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 8 }}>{t('executions', lang)}</h1>
        <p style={{ fontSize: 14, color: '#9CA3AF', marginBottom: 24 }}>{t('loading', lang)}</p>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>
            {t('executions', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {t('monitorExecutions', lang)}
            <span style={{ marginLeft: 8, color: '#6366F1' }}>{executions.length} {t('total', lang)}</span>
          </p>
        </div>
      </div>

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
              background: filter === f.key ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
              color: filter === f.key ? '#818CF8' : '#9CA3AF',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{
        background: '#161E2E', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)',
        overflow: 'hidden', overflowX: 'auto',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? 600 : undefined }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
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
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  cursor: 'pointer', transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                aria-label={`${t('executions', lang)} ${exec.run_id}`}
              >
                <td style={{ padding: '12px 16px' }}><StatusBadge status={exec.status} /></td>
                <td style={{ padding: '12px 16px', color: '#E5E7EB', fontSize: 14, fontWeight: 500 }}>{exec.workflow_name}</td>
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
