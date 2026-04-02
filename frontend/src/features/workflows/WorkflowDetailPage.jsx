import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import StatusBadge from '../../shared/components/StatusBadge'
import DataTable from '../../shared/components/DataTable'
import DAGVisualization from './DAGVisualization'

const DEMO_WORKFLOWS = {
  'wf-1': {
    id: 'wf-1', name: 'Análisis de Documentos',
    description: 'Pipeline completo para ingerir, clasificar, resumir y validar documentos automáticamente con agentes IA.',
    status: 'active', version: 'v1.3', created_at: '2026-03-20T10:30:00Z', updated_at: '2026-03-25T14:15:00Z',
    dag_definition: { steps: [
      { name: 'ingest', type: 'extractor', depends_on: [] },
      { name: 'classify', type: 'classifier', depends_on: ['ingest'] },
      { name: 'summarize', type: 'summarizer', depends_on: ['classify'] },
      { name: 'validate', type: 'validator', depends_on: ['summarize'] },
    ]},
  },
  'wf-2': {
    id: 'wf-2', name: 'Clasificación de Datos',
    description: 'Pipeline de clasificación con procesamiento paralelo y fusión de resultados.',
    status: 'active', version: 'v2.1', created_at: '2026-03-18T09:00:00Z', updated_at: '2026-03-24T11:00:00Z',
    dag_definition: { steps: [
      { name: 'load_data', type: 'extractor', depends_on: [] },
      { name: 'preprocess', type: 'normalizer', depends_on: ['load_data'] },
      { name: 'classify_a', type: 'classifier', depends_on: ['preprocess'] },
      { name: 'classify_b', type: 'classifier', depends_on: ['preprocess'] },
      { name: 'merge', type: 'enricher', depends_on: ['classify_a', 'classify_b'] },
      { name: 'export', type: 'validator', depends_on: ['merge'] },
    ]},
  },
  'wf-3': {
    id: 'wf-3', name: 'Resumen Ejecutivo',
    description: 'Genera resúmenes ejecutivos de documentos largos con puntos clave.',
    status: 'draft', version: 'v1.0', created_at: '2026-03-22T14:00:00Z', updated_at: '2026-03-22T14:00:00Z',
    dag_definition: { steps: [
      { name: 'extract', type: 'extractor', depends_on: [] },
      { name: 'summarize', type: 'summarizer', depends_on: ['extract'] },
    ]},
  },
  'wf-4': {
    id: 'wf-4', name: 'Extracción de Entidades',
    description: 'Extrae personas, organizaciones, fechas y montos de documentos.',
    status: 'paused', version: 'v1.1', created_at: '2026-03-15T08:30:00Z', updated_at: '2026-03-20T16:00:00Z',
    dag_definition: { steps: [
      { name: 'ingest', type: 'extractor', depends_on: [] },
      { name: 'ner', type: 'extractor', depends_on: ['ingest'] },
      { name: 'validate', type: 'validator', depends_on: ['ner'] },
    ]},
  },
  'wf-5': {
    id: 'wf-5', name: 'Pipeline RAG',
    description: 'Indexa documentos con embeddings y permite búsqueda semántica.',
    status: 'active', version: 'v3.0', created_at: '2026-03-10T10:00:00Z', updated_at: '2026-03-25T09:00:00Z',
    dag_definition: { steps: [
      { name: 'upload', type: 'extractor', depends_on: [] },
      { name: 'chunk', type: 'normalizer', depends_on: ['upload'] },
      { name: 'embed', type: 'enricher', depends_on: ['chunk'] },
      { name: 'index', type: 'validator', depends_on: ['embed'] },
      { name: 'search', type: 'knowledge', depends_on: ['index'] },
    ]},
  },
  'wf-6': {
    id: 'wf-6', name: 'Traducción Masiva',
    description: 'Traduce documentos a múltiples idiomas con verificación de calidad.',
    status: 'archived', version: 'v1.2', created_at: '2026-02-28T12:00:00Z', updated_at: '2026-03-10T15:00:00Z',
    dag_definition: { steps: [
      { name: 'extract', type: 'extractor', depends_on: [] },
      { name: 'translate', type: 'translator', depends_on: ['extract'] },
      { name: 'review', type: 'critic', depends_on: ['translate'] },
    ]},
  },
}

const DEFAULT_WORKFLOW = DEMO_WORKFLOWS['wf-1']

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

export default function WorkflowDetailPage({ workflowId, onBack, onEdit, lang = 'en' }) {
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState(null)
  const [demoRuns, setDemoRuns] = useState(DEMO_RUNS)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const wf = DEMO_WORKFLOWS[workflowId] || DEFAULT_WORKFLOW
  const runHistory = demoRuns

  const runColumns = [
    { key: 'status', label: t('status', lang), render: (v) => <StatusBadge status={v} /> },
    { key: 'started', label: t('start', lang) },
    { key: 'duration', label: t('duration', lang) },
    { key: 'cost', label: t('cost', lang) },
    { key: 'steps_done', label: t('steps', lang) },
  ]

  const handleRun = () => {
    setRunning(true)
    setRunError(null)
    // Demo mode: simulate execution
    setTimeout(() => {
      const newRun = {
        id: 'run-' + Date.now(),
        status: 'completed',
        started: new Date().toLocaleString(lang === 'es' ? 'es-ES' : 'en-US'),
        duration: `${Math.floor(Math.random() * 2 + 1)}m ${Math.floor(Math.random() * 50 + 10)}s`,
        cost: `$${(Math.random() * 0.3 + 0.05).toFixed(2)}`,
        steps_done: `${wf.dag_definition.steps.length}/${wf.dag_definition.steps.length}`,
      }
      setDemoRuns(prev => [newRun, ...prev])
      setRunning(false)
    }, 2000)
  }

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
            border: '1px solid #E5E7EB', background: 'transparent',
            color: '#9CA3AF', cursor: 'pointer', flexShrink: 0,
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#E5E7EB'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: isMobile ? 18 : 24, fontWeight: 700, color: '#111827' }}>{wf.name}</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF', marginTop: 2 }}>{wf.description}</p>
        </div>
        <div style={{
          display: 'flex', gap: 10,
          width: isMobile ? '100%' : 'auto',
        }}>
          <button
            onClick={onEdit || onBack}
            aria-label={t('edit', lang)}
            style={{
              padding: '10px 18px', borderRadius: 8, fontSize: 14,
              border: '1px solid #D1D5DB', background: 'transparent',
              color: '#111827', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
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
            background: '#FFFFFF', borderRadius: 10, padding: '14px 18px',
            border: '1px solid #E5E7EB',
            minWidth: isMobile ? 'calc(50% - 6px)' : 140,
            flex: isMobile ? '1 1 calc(50% - 6px)' : undefined,
          }}>
            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {info.label}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>
              {info.value}
            </div>
          </div>
        ))}
      </div>

      {/* DAG Visualization */}
      <div style={{
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid #E5E7EB', marginBottom: 24,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #E5E7EB',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>
            {t('executionGraph', lang)}
          </h3>
        </div>
        <DAGVisualization steps={wf.dag_definition?.steps || []} />
      </div>

      {/* Run history */}
      <div style={{
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid #E5E7EB', overflow: 'hidden',
        overflowX: 'auto',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #E5E7EB',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>
            {t('executionHistory', lang)}
          </h3>
        </div>
        <DataTable columns={runColumns} data={runHistory} pageSize={5} />
      </div>
    </div>
  )
}
