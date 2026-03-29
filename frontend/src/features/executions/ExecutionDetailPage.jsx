import { useState, useEffect, useRef } from 'react'
import { api } from '../../api/client'
import { t } from '../../shared/i18n/translations'
import { connectExecutionWS } from '../../api/websocket'
import StatusBadge from '../../shared/components/StatusBadge'
import StepTimeline from './StepTimeline'
import LiveLog from './LiveLog'

const DEMO_EXECUTION = {
  run_id: 'run-001',
  workflow_name: 'Clasificar Documentos',
  status: 'completed',
  started_at: '2026-03-26T09:12:00Z',
  finished_at: '2026-03-26T09:12:14Z',
  total_cost: 0.032,
  total_tokens: 4520,
  steps: [
    { name: 'Cargar Documento', agent_type: 'loader', status: 'completed', duration_ms: 1200, tokens: 0, tokens_in: 0, tokens_out: 0, cost: 0, model: null, provider: 'local', retries: 0, fallback_used: false, input: { file: 'contrato.pdf', format: 'application/pdf' }, output: { pages: 12, text_length: 14500, encoding: 'utf-8' } },
    { name: 'Clasificar Tipo', agent_type: 'classifier', status: 'completed', duration_ms: 3400, tokens: 1820, tokens_in: 1540, tokens_out: 280, cost: 0.012, model: 'llama-3.3-70b', provider: 'Groq', retries: 0, fallback_used: false, input: { text: '(documento completo — 14,500 chars)', prompt_template: 'classify_document_v2' }, output: { type: 'legal_contract', confidence: 0.94, sub_type: 'service_agreement', language: 'es' } },
    { name: 'Extraer Entidades', agent_type: 'extractor', status: 'completed', duration_ms: 5100, tokens: 2200, tokens_in: 1800, tokens_out: 400, cost: 0.015, model: 'claude-sonnet-4-20250514', provider: 'Anthropic', retries: 1, fallback_used: true, fallback_provider: 'Anthropic (from Groq)', input: { text: '(documento completo)', type: 'legal_contract', extraction_schema: 'entities_v3' }, output: { entities: ['Empresa A', 'Empresa B'], dates: ['2026-01-15', '2027-01-15'], amounts: ['$45,000 USD'], clauses: 12 } },
    { name: 'Guardar Resultado', agent_type: 'storage', status: 'completed', duration_ms: 800, tokens: 500, tokens_in: 480, tokens_out: 20, cost: 0.005, model: null, provider: 'PostgreSQL', retries: 0, fallback_used: false, input: { doc_id: 'doc-123', index_target: 'pgvector' }, output: { stored: true, index_id: 'idx-456', vector_dims: 1536, chunks_indexed: 24 } },
  ],
}

const DEMO_EVENTS = [
  { timestamp: '2026-03-26T09:12:00Z', event_type: 'step_started', step_name: 'Cargar Documento', detail: 'Iniciando carga de contrato.pdf' },
  { timestamp: '2026-03-26T09:12:01Z', event_type: 'step_completed', step_name: 'Cargar Documento', detail: '12 páginas procesadas' },
  { timestamp: '2026-03-26T09:12:02Z', event_type: 'step_started', step_name: 'Clasificar Tipo', detail: 'Enviando a agente classifier' },
  { timestamp: '2026-03-26T09:12:05Z', event_type: 'step_completed', step_name: 'Clasificar Tipo', detail: 'legal_contract (94%)' },
  { timestamp: '2026-03-26T09:12:06Z', event_type: 'step_started', step_name: 'Extraer Entidades', detail: 'Ejecutando extractor' },
  { timestamp: '2026-03-26T09:12:11Z', event_type: 'step_completed', step_name: 'Extraer Entidades', detail: '2 entidades, 2 fechas' },
  { timestamp: '2026-03-26T09:12:12Z', event_type: 'step_started', step_name: 'Guardar Resultado', detail: 'Guardando en storage' },
  { timestamp: '2026-03-26T09:12:14Z', event_type: 'step_completed', step_name: 'Guardar Resultado', detail: 'Indexado como idx-456' },
]

function formatDuration(ms) {
  if (!ms) return '--'
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  const locale = lang === 'es' ? 'es-ES' : 'en-US'
  return new Date(iso).toLocaleString(locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function ExecutionDetailPage({ runId, onBack, lang = 'en' }) {
  const [execution, setExecution] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [elapsed, setElapsed] = useState(0)
  const [isMobile, setIsMobile] = useState(false)
  const wsRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await api.get(`/executions/${runId}`)
        if (!cancelled) setExecution(data)
      } catch {
        if (!cancelled) {
          setExecution({ ...DEMO_EXECUTION, run_id: runId })
          setEvents(DEMO_EVENTS)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [runId])

  // WebSocket for live updates
  useEffect(() => {
    if (!execution || execution.status === 'completed' || execution.status === 'failed') return
    try {
      wsRef.current = connectExecutionWS(runId, (msg) => {
        if (msg.type === 'step_update' && msg.step) {
          setExecution((prev) => {
            if (!prev) return prev
            const steps = prev.steps.map((s) =>
              s.name === msg.step.name ? { ...s, ...msg.step } : s
            )
            return { ...prev, steps, status: msg.run_status || prev.status }
          })
        }
        if (msg.type === 'event' || msg.event_type) {
          setEvents((prev) => [...prev, msg])
        }
      })
    } catch { /* WS unavailable */ }
    return () => { wsRef.current?.close() }
  }, [execution?.status, runId])

  // Running timer
  useEffect(() => {
    if (execution?.status === 'running' && execution.started_at) {
      timerRef.current = setInterval(() => {
        setElapsed(Date.now() - new Date(execution.started_at).getTime())
      }, 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [execution?.status, execution?.started_at])

  if (loading) {
    return (
      <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
        <button onClick={onBack} aria-label={t('back', lang)} style={backBtnStyle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
          {t('backToExecutions', lang)}
        </button>
        <p style={{ color: '#9CA3AF', marginTop: 24 }}>{t('loadingExecution', lang)}</p>
      </div>
    )
  }

  if (!execution) return null

  const completedSteps = execution.steps?.filter((s) => s.status === 'completed').length || 0
  const totalSteps = execution.steps?.length || 0
  const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0
  const isFinished = execution.status === 'completed' || execution.status === 'failed'
  const totalDuration = isFinished
    ? (execution.finished_at && execution.started_at
        ? new Date(execution.finished_at) - new Date(execution.started_at)
        : execution.duration_ms)
    : elapsed

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Back button */}
      <button onClick={onBack} aria-label={t('back', lang)} style={backBtnStyle}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
        {t('backToExecutions', lang)}
      </button>

      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginTop: 16, marginBottom: 24, flexWrap: 'wrap', gap: 16,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, color: '#111827', margin: 0 }}>{execution.workflow_name}</h1>
            <StatusBadge status={execution.status} />
          </div>
          <span style={{ fontSize: 13, color: '#9CA3AF', fontFamily: 'monospace' }}>{execution.run_id}</span>
        </div>
        <div style={{
          display: 'flex', gap: isMobile ? 12 : 20,
          flexWrap: 'wrap',
        }}>
          {[
            { label: t('duration', lang), value: formatDuration(totalDuration) },
            { label: t('cost', lang), value: `$${execution.total_cost?.toFixed(3) || '0.000'}`, color: '#10B981' },
            { label: t('tokens', lang), value: execution.total_tokens?.toLocaleString() || '0' },
          ].map((m) => (
            <div key={m.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 4 }}>{m.label}</div>
              <div style={{ fontSize: isMobile ? 16 : 18, fontWeight: 700, color: m.color || '#111827' }}>{m.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>{t('progress', lang)}</span>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>{completedSteps}/{totalSteps} {t('steps', lang).toLowerCase()}</span>
        </div>
        <div style={{
          height: 6, borderRadius: 3, background: '#E5E7EB', overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', borderRadius: 3, width: `${progress}%`,
            background: execution.status === 'failed' ? '#EF4444' : 'linear-gradient(90deg, #2563EB, #3B82F6)',
            transition: 'width 0.5s ease',
          }} />
        </div>
      </div>

      {/* Timeline */}
      <div data-tour="step-timeline" style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16 }}>
          {t('executionPipeline', lang)}
        </h2>
        <StepTimeline steps={execution.steps || []} />
      </div>

      {/* Log panel */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 12 }}>
          {t('eventLog', lang)}
        </h2>
        <LiveLog events={events} />
      </div>

      {/* Summary if finished */}
      {isFinished && (
        <div style={{
          background: execution.status === 'completed' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${execution.status === 'completed' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
          borderRadius: 10, padding: 20,
        }}>
          <h3 style={{
            fontSize: 14, fontWeight: 600, marginBottom: 10,
            color: execution.status === 'completed' ? '#10B981' : '#EF4444',
          }}>
            {execution.status === 'completed' ? t('executionCompleted', lang) : t('executionFailed', lang)}
          </h3>
          <div style={{ display: 'flex', gap: isMobile ? 12 : 24, flexWrap: 'wrap', fontSize: 13, color: '#374151' }}>
            <span>{t('totalTime', lang)}: <strong>{formatDuration(totalDuration)}</strong></span>
            <span>{t('totalCost', lang)}: <strong style={{ color: '#10B981' }}>${execution.total_cost?.toFixed(3)}</strong></span>
            <span>{t('tokensUsed', lang)}: <strong>{execution.total_tokens?.toLocaleString()}</strong></span>
            <span>{t('start', lang)}: <strong>{formatDate(execution.started_at, lang)}</strong></span>
          </div>
        </div>
      )}
    </div>
  )
}

const backBtnStyle = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  padding: '6px 12px', borderRadius: 8, border: 'none',
  background: '#F3F4F6', color: '#9CA3AF',
  fontSize: 13, cursor: 'pointer', transition: 'all 0.15s',
}
