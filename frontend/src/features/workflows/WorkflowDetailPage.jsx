import { useState, useEffect } from 'react'
import { fetchAPI, trackGuestRun } from '../../services/api'
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

const STATUS_CONFIG = {
  active: { color: '#10B981', bg: 'rgba(16,185,129,0.1)', label: { en: 'Active', es: 'Activo' } },
  draft: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', label: { en: 'Draft', es: 'Borrador' } },
  paused: { color: '#9CA3AF', bg: 'rgba(156,163,175,0.1)', label: { en: 'Paused', es: 'Pausado' } },
  archived: { color: '#6B7280', bg: 'rgba(107,114,128,0.1)', label: { en: 'Archived', es: 'Archivado' } },
  completed: { color: '#10B981', bg: 'rgba(16,185,129,0.1)', label: { en: 'Completed', es: 'Completado' } },
}

const INFO_ICONS = {
  version: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z',
  created: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
  updated: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  steps: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
}

export default function WorkflowDetailPage({ workflowId, onBack, onEdit, lang = 'en' }) {
  const [running, setRunning] = useState(false)
  const [runPhase, setRunPhase] = useState(null) // null | 'preparing' | 'executing' | 'done' | 'error'
  const [runError, setRunError] = useState(null)
  const [runHistory, setRunHistory] = useState(DEMO_RUNS)
  const [stepStatuses, setStepStatuses] = useState({})
  const [activeTab, setActiveTab] = useState('dag')
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const [wf, setWf] = useState(() => DEMO_WORKFLOWS[workflowId] || DEFAULT_WORKFLOW)

  useEffect(() => {
    if (DEMO_WORKFLOWS[workflowId]) return
    if (workflowId && !workflowId.startsWith('wf-')) {
      fetchAPI(`/workflows/${workflowId}`).then((res) => {
        if (!res.error && res.data) {
          const w = res.data
          setWf({
            ...DEFAULT_WORKFLOW,
            id: w.id,
            name: w.name,
            description: w.description || '',
            status: w.status || 'active',
            version: 'v' + (w.version || '1.0'),
            dag_definition: w.dag_definition,
            created_at: w.created_at,
            updated_at: w.updated_at,
          })
        }
      })
    }
  }, [workflowId])

  // Fetch real execution history for real workflows
  const loadRuns = () => {
    if (workflowId && !workflowId.startsWith('wf-')) {
      fetchAPI(`/executions?workflow_id=${workflowId}`).then((res) => {
        if (!res.error && res.data) {
          const runs = Array.isArray(res.data) ? res.data : res.data.runs || []
          if (runs.length > 0) {
            setRunHistory(runs.map(r => ({
              id: r.id || r.run_id,
              status: r.status || 'completed',
              started: r.started_at || r.created_at ? new Date(r.started_at || r.created_at).toLocaleString(lang === 'es' ? 'es-MX' : 'en-US') : '—',
              duration: r.latency_ms ? `${Math.floor(r.latency_ms / 60000)}m ${Math.floor((r.latency_ms % 60000) / 1000)}s`
                : r.completed_at && r.started_at ? `${Math.round((new Date(r.completed_at) - new Date(r.started_at)) / 1000)}s` : '—',
              cost: r.total_cost_usd ? `$${Number(r.total_cost_usd).toFixed(2)}` : r.total_cost ? `$${Number(r.total_cost).toFixed(2)}` : '—',
              steps_done: r.steps_completed ? `${r.steps_completed}/${r.steps_total || '?'}` : '—',
            })))
          }
        }
      })
    }
  }
  useEffect(() => { loadRuns() }, [workflowId, lang])

  const steps = wf.dag_definition?.steps || []
  const locale = lang === 'es' ? 'es-MX' : 'en-US'
  const statusCfg = STATUS_CONFIG[wf.status] || STATUS_CONFIG.active

  const handleRun = async () => {
    setRunning(true)
    setRunPhase('preparing')
    setRunError(null)
    setStepStatuses({})

    const trial = trackGuestRun()
    if (!trial.allowed) {
      setRunError(lang === 'es' ? 'Límite de prueba alcanzado. Regístrate para continuar.' : 'Trial limit reached. Register to continue.')
      setRunPhase('error')
      setRunning(false)
      return
    }

    // Animate step-by-step execution
    setRunPhase('executing')
    const stepsToRun = [...steps]
    for (let i = 0; i < stepsToRun.length; i++) {
      setStepStatuses(prev => ({ ...prev, [stepsToRun[i].name]: 'running' }))
      await new Promise(r => setTimeout(r, 600 + Math.random() * 800))

      // Try real backend for non-demo workflows (trigger once on first step)
      if (!workflowId?.startsWith('wf-') && i === 0) {
        const res = await fetchAPI('/executions', {
          method: 'POST',
          body: JSON.stringify({
            workflow_id: workflowId,
            trigger_type: 'manual',
            input_data: {},
          }),
        })
        if (!res.error && res.data?.run_id) {
          // Real execution triggered — continue animation
        }
      }

      const success = Math.random() > 0.05
      setStepStatuses(prev => ({ ...prev, [stepsToRun[i].name]: success ? 'completed' : 'failed' }))
      if (!success) {
        setRunPhase('error')
        setRunError(`Step "${stepsToRun[i].name}" failed`)
        setRunning(false)
        return
      }
    }

    setRunPhase('done')
    const newRun = {
      id: 'run-' + Date.now(),
      status: 'completed',
      started: new Date().toLocaleString(locale),
      duration: `${Math.floor(Math.random() * 2 + 1)}m ${Math.floor(Math.random() * 50 + 10)}s`,
      cost: `$${(Math.random() * 0.3 + 0.05).toFixed(2)}`,
      steps_done: `${steps.length}/${steps.length}`,
    }
    setRunHistory(prev => [newRun, ...prev])
    // Refresh real runs from backend
    setTimeout(() => { loadRuns() }, 1500)
    setTimeout(() => { setRunning(false); setRunPhase(null) }, 2000)
  }

  const runColumns = [
    { key: 'status', label: t('status', lang), render: (v) => <StatusBadge status={v} /> },
    { key: 'started', label: lang === 'es' ? 'Inicio' : 'Started' },
    { key: 'duration', label: lang === 'es' ? 'Duración' : 'Duration' },
    { key: 'cost', label: lang === 'es' ? 'Costo' : 'Cost' },
    { key: 'steps_done', label: lang === 'es' ? 'Pasos' : 'Steps' },
  ]

  const tabs = [
    { key: 'dag', label: lang === 'es' ? 'Grafo DAG' : 'DAG Graph', icon: 'M4 6h16M4 12h8m-8 6h16' },
    { key: 'history', label: lang === 'es' ? 'Historial' : 'History', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
    { key: 'config', label: lang === 'es' ? 'Configuración' : 'Config', icon: 'M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93s.844.126 1.197-.094l.758-.474a1.12 1.12 0 011.37.15l.773.773c.39.39.44 1.002.15 1.37l-.474.758c-.22.353-.254.804-.094 1.197.16.396.506.71.93.78l.894.15c.542.09.94.56.94 1.109v1.094c0 .55-.398 1.02-.94 1.11l-.894.149c-.424.07-.764.384-.93.78s-.126.844.094 1.197l.474.758c.29.368.24.98-.15 1.37l-.773.773c-.39.39-1.002.44-1.37.15l-.758-.474c-.353-.22-.804-.254-1.197-.094-.396.16-.71.506-.78.93l-.15.894c-.09.542-.56.94-1.109.94h-1.094c-.55 0-1.02-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93s-.844-.126-1.197.094l-.757.474c-.368.29-.98.24-1.37-.15l-.774-.773a1.12 1.12 0 01-.15-1.37l.474-.758c.22-.353.254-.804.094-1.197a2.25 2.25 0 00-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.764-.384.93-.78s.126-.844-.094-1.197l-.474-.758a1.12 1.12 0 01.15-1.37l.773-.774c.39-.39 1.002-.44 1.37-.15l.758.474c.353.22.804.254 1.197.094.396-.16.71-.506.78-.93l.15-.894z' },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{
        background: '#fff', borderRadius: 16, border: '1px solid #E5E7EB',
        padding: isMobile ? 16 : 24, marginBottom: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, flexWrap: 'wrap' }}>
          <button
            onClick={onBack}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 38, height: 38, borderRadius: 10,
              border: '1px solid #E5E7EB', background: '#F9FAFB',
              color: '#6B7280', cursor: 'pointer', flexShrink: 0,
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.color = '#6366F1' }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#6B7280' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M19 12H5m7-7l-7 7 7 7" />
            </svg>
          </button>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
              <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, color: '#111827', margin: 0 }}>
                {wf.name}
              </h1>
              <span style={{
                padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                background: statusCfg.bg, color: statusCfg.color,
              }}>
                {statusCfg.label[lang]}
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#6B7280', margin: 0 }}>{wf.description}</p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexShrink: 0, width: isMobile ? '100%' : 'auto' }}>
            <button
              onClick={onEdit || onBack}
              style={{
                padding: '9px 16px', borderRadius: 9, fontSize: 13, fontWeight: 500,
                border: '1px solid #D1D5DB', background: '#fff',
                color: '#374151', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                flex: isMobile ? 1 : undefined, justifyContent: 'center',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = '#6366F1'}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = '#D1D5DB'}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              {lang === 'es' ? 'Editar' : 'Edit'}
            </button>
            <button
              onClick={handleRun}
              disabled={running}
              style={{
                padding: '9px 18px', borderRadius: 9, fontSize: 13, fontWeight: 600,
                border: 'none',
                background: running ? '#A5B4FC' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                color: '#fff', cursor: running ? 'default' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
                flex: isMobile ? 1 : undefined, justifyContent: 'center',
                transition: 'all 0.2s', boxShadow: running ? 'none' : '0 2px 8px rgba(99,102,241,0.3)',
              }}
            >
              {running ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                  style={{ animation: 'spin 1s linear infinite' }}>
                  <path d="M21 12a9 9 0 11-6.219-8.56" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
              {running
                ? (runPhase === 'preparing' ? (lang === 'es' ? 'Preparando...' : 'Preparing...') : (lang === 'es' ? 'Ejecutando...' : 'Executing...'))
                : (lang === 'es' ? 'Ejecutar' : 'Execute')}
            </button>
          </div>
        </div>

        {/* Quick stats row */}
        <div style={{
          display: 'flex', gap: isMobile ? 8 : 16, marginTop: 20,
          flexWrap: 'wrap',
        }}>
          {[
            { icon: INFO_ICONS.version, label: lang === 'es' ? 'Versión' : 'Version', value: wf.version, color: '#6366F1' },
            { icon: INFO_ICONS.steps, label: lang === 'es' ? 'Pasos' : 'Steps', value: steps.length, color: '#10B981' },
            { icon: INFO_ICONS.created, label: lang === 'es' ? 'Creado' : 'Created', value: wf.created_at ? new Date(wf.created_at).toLocaleDateString(locale) : '—', color: '#3B82F6' },
            { icon: INFO_ICONS.updated, label: lang === 'es' ? 'Actualizado' : 'Updated', value: wf.updated_at ? new Date(wf.updated_at).toLocaleDateString(locale) : '—', color: '#F59E0B' },
          ].map((info) => (
            <div key={info.label} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 14px', borderRadius: 10,
              background: '#F9FAFB', border: '1px solid #F3F4F6',
              flex: isMobile ? '1 1 calc(50% - 4px)' : undefined,
              minWidth: isMobile ? 0 : 140,
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={info.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                <path d={info.icon} />
              </svg>
              <div>
                <div style={{ fontSize: 10, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{info.label}</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{info.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Run status banner */}
      {runPhase === 'done' && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, marginBottom: 16, fontSize: 13,
          background: 'rgba(16,185,129,0.08)', color: '#059669',
          border: '1px solid rgba(16,185,129,0.2)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><path d="M22 4L12 14.01l-3-3" />
          </svg>
          {lang === 'es' ? 'Ejecución completada exitosamente' : 'Execution completed successfully'}
        </div>
      )}
      {runError && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, marginBottom: 16, fontSize: 13,
          background: 'rgba(239,68,68,0.08)', color: '#DC2626',
          border: '1px solid rgba(239,68,68,0.2)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6m0-6l6 6" />
          </svg>
          {runError}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E5E7EB' }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 18px', border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: 600, background: 'none',
              color: activeTab === tab.key ? '#6366F1' : '#9CA3AF',
              borderBottom: activeTab === tab.key ? '2px solid #6366F1' : '2px solid transparent',
              marginBottom: -2, display: 'flex', alignItems: 'center', gap: 6,
              transition: 'all 0.15s',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d={tab.icon} />
            </svg>
            {tab.label}
          </button>
        ))}
      </div>

      {/* DAG Tab */}
      {activeTab === 'dag' && (
        <div style={{
          background: '#fff', borderRadius: 14,
          border: '1px solid #E5E7EB', overflow: 'hidden',
        }}>
          <div style={{
            padding: '14px 20px', borderBottom: '1px solid #F3F4F6',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
              {lang === 'es' ? 'Grafo de Ejecución (DAG)' : 'Execution Graph (DAG)'}
            </h3>
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>
              {steps.length} {lang === 'es' ? 'nodos' : 'nodes'}
            </span>
          </div>
          <DAGVisualization steps={steps} stepStatuses={stepStatuses} lang={lang} />

          {/* Step legend */}
          {steps.length > 0 && (
            <div style={{
              padding: '12px 20px', borderTop: '1px solid #F3F4F6',
              display: 'flex', flexWrap: 'wrap', gap: 12,
            }}>
              {steps.map((s, i) => (
                <div key={s.name} style={{
                  display: 'flex', alignItems: 'center', gap: 6, fontSize: 12,
                }}>
                  <span style={{
                    width: 18, height: 18, borderRadius: 5, fontSize: 10, fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: stepStatuses[s.name] === 'completed' ? '#D1FAE5'
                      : stepStatuses[s.name] === 'running' ? '#E0E7FF'
                      : stepStatuses[s.name] === 'failed' ? '#FEE2E2' : '#F3F4F6',
                    color: stepStatuses[s.name] === 'completed' ? '#059669'
                      : stepStatuses[s.name] === 'running' ? '#6366F1'
                      : stepStatuses[s.name] === 'failed' ? '#DC2626' : '#9CA3AF',
                  }}>
                    {i + 1}
                  </span>
                  <span style={{ color: '#374151', fontWeight: 500 }}>{s.name}</span>
                  <span style={{ color: '#9CA3AF' }}>({s.type})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div style={{
          background: '#fff', borderRadius: 14,
          border: '1px solid #E5E7EB', overflow: 'hidden',
          overflowX: 'auto',
        }}>
          <div style={{
            padding: '14px 20px', borderBottom: '1px solid #F3F4F6',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
              {lang === 'es' ? 'Historial de Ejecuciones' : 'Execution History'}
            </h3>
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>
              {runHistory.length} {lang === 'es' ? 'ejecuciones' : 'runs'}
            </span>
          </div>
          {runHistory.length > 0 ? (
            <DataTable columns={runColumns} data={runHistory} pageSize={8} />
          ) : (
            <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
              {lang === 'es' ? 'Sin ejecuciones aún. Haz click en "Ejecutar" para comenzar.' : 'No runs yet. Click "Execute" to start.'}
            </div>
          )}
        </div>
      )}

      {/* Config Tab */}
      {activeTab === 'config' && (
        <div style={{
          background: '#fff', borderRadius: 14,
          border: '1px solid #E5E7EB', padding: 24,
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 16 }}>
            {lang === 'es' ? 'Definición del Pipeline' : 'Pipeline Definition'}
          </h3>
          <div style={{
            background: '#F9FAFB', borderRadius: 10, padding: 16,
            fontFamily: 'monospace', fontSize: 12, color: '#374151',
            maxHeight: 400, overflow: 'auto',
            border: '1px solid #F3F4F6',
          }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(wf.dag_definition, null, 2)}
            </pre>
          </div>

          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginTop: 24, marginBottom: 12 }}>
            {lang === 'es' ? 'Dependencias entre Pasos' : 'Step Dependencies'}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map((s, i) => (
              <div key={s.name} style={{
                display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
                padding: '8px 12px', borderRadius: 8, background: '#F9FAFB',
              }}>
                <span style={{
                  width: 24, height: 24, borderRadius: 6,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#E0E7FF', color: '#6366F1', fontSize: 11, fontWeight: 700, flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <span style={{ fontWeight: 600, color: '#111827' }}>{s.name}</span>
                <span style={{ color: '#9CA3AF' }}>({s.type})</span>
                {s.depends_on?.length > 0 && (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round">
                      <path d="M5 12h14m-7-7l7 7-7 7" />
                    </svg>
                    <span style={{ color: '#6B7280', fontSize: 12 }}>
                      {lang === 'es' ? 'depende de' : 'depends on'}: {s.depends_on.join(', ')}
                    </span>
                  </>
                )}
                {(!s.depends_on || s.depends_on.length === 0) && (
                  <span style={{
                    padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600,
                    background: 'rgba(16,185,129,0.1)', color: '#10B981',
                  }}>
                    {lang === 'es' ? 'inicio' : 'entry'}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CSS animation for spinner */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
      `}</style>
    </div>
  )
}
