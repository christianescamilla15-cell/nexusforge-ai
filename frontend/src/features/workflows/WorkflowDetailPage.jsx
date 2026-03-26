import { useState, useEffect } from 'react'
import { useAPI } from '../../shared/hooks/useAPI'
import { t } from '../../shared/i18n/translations'
import StatusBadge from '../../shared/components/StatusBadge'
import DataTable from '../../shared/components/DataTable'
import LoadingSpinner from '../../shared/components/LoadingSpinner'
import DAGVisualization from './DAGVisualization'
import { api } from '../../api/client'

const DEMO_WORKFLOW = {
  id: 'wf-1',
  name: 'Analisis de Documentos',
  description: 'Pipeline completo para ingerir, clasificar, resumir y validar documentos automaticamente con agentes IA.',
  status: 'active',
  version: 'v1.3',
  created_at: '2026-03-20T10:30:00Z',
  updated_at: '2026-03-25T14:15:00Z',
  dag_definition: {
    steps: [
      { name: 'ingest', type: 'extractor', depends_on: [] },
      { name: 'classify', type: 'classifier', depends_on: ['ingest'] },
      { name: 'summarize', type: 'summarizer', depends_on: ['classify'] },
      { name: 'validate', type: 'validator', depends_on: ['summarize'] },
    ],
  },
}

const DEMO_RUNS = [
  { id: 'run-1', status: 'completed', started: '2026-03-25 14:10', duration: '2m 14s', cost: '$0.23', steps_done: '4/4' },
  { id: 'run-2', status: 'completed', started: '2026-03-25 10:30', duration: '1m 58s', cost: '$0.19', steps_done: '4/4' },
  { id: 'run-3', status: 'failed', started: '2026-03-24 16:45', duration: '1m 02s', cost: '$0.11', steps_done: '2/4' },
  { id: 'run-4', status: 'completed', started: '2026-03-24 09:00', duration: '2m 30s', cost: '$0.25', steps_done: '4/4' },
]

const statusMap = {
  active: 'completed',
  draft: 'pending',
  paused: 'cancelled',
  archived: 'pending',
}

export default function WorkflowDetailPage({ workflowId, onBack, lang = 'en' }) {
  const { data: workflow, loading, error } = useAPI(`/workflows/${workflowId}`)
  const { data: runs, loading: runsLoading } = useAPI(`/workflows/${workflowId}/runs`)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const wf = workflow || DEMO_WORKFLOW
  const runHistory = runs || DEMO_RUNS

  const runColumns = [
    { key: 'status', label: t('status', lang), render: (v) => <StatusBadge status={v} /> },
    { key: 'started', label: t('start', lang) },
    { key: 'duration', label: t('duration', lang) },
    { key: 'cost', label: t('cost', lang) },
    { key: 'steps_done', label: t('steps', lang) },
  ]

  const handleRun = async () => {
    setRunning(true)
    setRunError(null)
    try {
      await api.post(`/workflows/${workflowId}/run`, {})
    } catch (e) {
      setRunError(e.message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingSpinner />

  const locale = lang === 'es' ? 'es-ES' : 'en-US'

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24,
        flexWrap: isMobile ? 'wrap' : 'nowrap',
      }}>
        <button
          onClick={onBack}
          aria-label={t('back', lang)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 36, height: 36, borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.08)', background: 'transparent',
            color: '#9CA3AF', cursor: 'pointer', flexShrink: 0,
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 18 : 24, fontWeight: 700, color: '#E5E7EB' }}>{wf.name}</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF', marginTop: 2 }}>{wf.description}</p>
        </div>
        <div style={{
          display: 'flex', gap: 10,
          width: isMobile ? '100%' : 'auto',
        }}>
          <button
            onClick={onBack}
            aria-label={t('edit', lang)}
            style={{
              padding: '10px 18px', borderRadius: 8, fontSize: 14,
              border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
              color: '#E5E7EB', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
              flex: isMobile ? 1 : undefined, justifyContent: 'center',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            {t('edit', lang)}
          </button>
          <button
            onClick={handleRun}
            disabled={running}
            aria-label={t('execute', lang)}
            style={{
              padding: '10px 18px', borderRadius: 8, fontSize: 14, fontWeight: 500,
              border: 'none', background: '#6366F1', color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              opacity: running ? 0.6 : 1,
              flex: isMobile ? 1 : undefined, justifyContent: 'center',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            {running ? t('starting', lang) : t('execute', lang)}
          </button>
        </div>
      </div>

      {runError && (
        <div style={{
          padding: '10px 16px', borderRadius: 8, marginBottom: 16, fontSize: 13,
          background: 'rgba(239,68,68,0.1)', color: '#EF4444',
          border: '1px solid rgba(239,68,68,0.2)',
        }}>
          {t('errorExecuting', lang)}: {runError}
        </div>
      )}

      {/* Info cards row */}
      <div style={{
        display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24,
      }}>
        {[
          { label: t('status', lang), value: <StatusBadge status={statusMap[wf.status] || wf.status} /> },
          { label: t('version', lang), value: wf.version },
          { label: t('created', lang), value: new Date(wf.created_at).toLocaleDateString(locale) },
          { label: t('updated', lang), value: new Date(wf.updated_at).toLocaleDateString(locale) },
          { label: t('steps', lang), value: wf.dag_definition?.steps?.length || 0 },
        ].map((info) => (
          <div key={info.label} style={{
            background: '#161E2E', borderRadius: 10, padding: '14px 18px',
            border: '1px solid rgba(255,255,255,0.06)',
            minWidth: isMobile ? 'calc(50% - 6px)' : 140,
            flex: isMobile ? '1 1 calc(50% - 6px)' : undefined,
          }}>
            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {info.label}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
              {info.value}
            </div>
          </div>
        ))}
      </div>

      {/* DAG Visualization */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', marginBottom: 24,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
            {t('executionGraph', lang)}
          </h3>
        </div>
        <DAGVisualization steps={wf.dag_definition?.steps || []} />
      </div>

      {/* Run history */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
        overflowX: 'auto',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
            {t('executionHistory', lang)}
          </h3>
        </div>
        {runsLoading ? (
          <LoadingSpinner />
        ) : (
          <DataTable columns={runColumns} data={runHistory} pageSize={5} />
        )}
      </div>
    </div>
  )
}
