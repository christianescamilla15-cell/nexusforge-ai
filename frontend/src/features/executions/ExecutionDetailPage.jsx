import { useState, useEffect, useRef } from 'react'
import { fetchAPI } from '../../services/api'
import { t } from '../../shared/i18n/translations'
import StatusBadge from '../../shared/components/StatusBadge'
import StepTimeline from './StepTimeline'
import LiveLog from './LiveLog'


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
        const res = await fetchAPI(`/executions/${runId}`)
        if (!cancelled) {
          if (res.error) throw new Error(res.error)
          const data = res.data || {}
          const mapped = {
            run_id: data.id || data.run_id || runId,
            workflow_name: data.workflow_name || 'Workflow',
            status: data.status || 'completed',
            started_at: data.started_at || data.created_at,
            finished_at: data.finished_at || data.completed_at,
            total_cost: data.total_cost_usd || data.total_cost || data.cost || 0,
            total_tokens: data.total_tokens || data.tokens || 0,
            duration_ms: data.total_latency_ms || data.latency_ms
              || (data.completed_at && data.started_at ? new Date(data.completed_at) - new Date(data.started_at) : null),
            steps: Array.isArray(data.steps) && data.steps.length > 0 && typeof data.steps[0] === 'object'
              ? data.steps.map(s => ({
                  name: s.step_name || s.name || 'Step',
                  agent_type: s.agent_type || s.step_type || 'agent',
                  status: s.status || 'completed',
                  duration_ms: s.duration_ms || 0,
                  tokens: s.tokens_used || s.tokens || 0,
                  tokens_in: s.tokens_in || null,
                  tokens_out: s.tokens_out || null,
                  cost: s.cost_usd != null ? s.cost_usd : (s.cost || 0),
                  model: s.model || null,
                  provider: s.provider || null,
                  retries: s.retry_count || s.retries || 0,
                  fallback_used: s.fallback_used || false,
                  input: s.input_data || s.input || null,
                  output: s.output_data || s.output || null,
                  error: s.error_message || s.error || null,
                }))
              : (data.agents_used || []).map((agent) => ({
                  name: agent,
                  agent_type: agent.toLowerCase().replace('agent', ''),
                  status: data.status === 'failed' ? 'failed' : 'completed',
                  duration_ms: Math.round((data.total_latency_ms || 1000) / (data.agents_used?.length || 1)),
                  tokens: Math.round((data.total_tokens || 0) / (data.agents_used?.length || 1)),
                  cost: (data.total_cost_usd || data.total_cost || 0) / (data.agents_used?.length || 1),
                  provider: 'groq',
                  model: 'llama-3.3-70b-versatile',
                  retries: 0,
                  fallback_used: false,
                })),
          }
          setExecution(mapped)

          // Generate events for the LiveLog
          const generatedEvents = []
          const baseTime = mapped.started_at ? new Date(mapped.started_at) : new Date()

          // Always add a run_started event
          generatedEvents.push({
            timestamp: baseTime.toISOString(),
            event_type: 'info',
            step_name: '',
            detail: `Run ${mapped.run_id.slice(0, 8)}… iniciado — workflow: ${mapped.workflow_name}`,
          })

          if (mapped.steps.length > 0) {
            let timeOffset = 0
            mapped.steps.forEach((step) => {
              generatedEvents.push({
                timestamp: new Date(baseTime.getTime() + timeOffset).toISOString(),
                event_type: 'step_started',
                step_name: step.name,
                detail: `Ejecutando ${step.agent_type || 'agente'}${step.model ? ` (${step.model})` : ''}`,
              })
              timeOffset += step.duration_ms || 1000
              generatedEvents.push({
                timestamp: new Date(baseTime.getTime() + timeOffset).toISOString(),
                event_type: step.status === 'failed' ? 'step_failed' : 'step_completed',
                step_name: step.name,
                detail: step.status === 'failed'
                  ? (step.error || 'Error en ejecución')
                  : `${step.tokens?.toLocaleString() || 0} tokens, ${step.duration_ms || 0}ms`,
              })
            })
          } else {
            // No steps — check if stuck
            const elapsedMin = (Date.now() - baseTime.getTime()) / 60000
            if (mapped.status === 'pending' || mapped.status === 'running') {
              generatedEvents.push({
                timestamp: new Date().toISOString(),
                event_type: 'warning',
                step_name: '',
                detail: elapsedMin > 5
                  ? `Ejecución en espera hace ${Math.floor(elapsedMin)} min — el backend puede estar procesando o el run se colgó`
                  : 'Esperando que el backend inicie la ejecución del DAG…',
              })
            }
            if (mapped.status === 'completed' || mapped.status === 'failed') {
              generatedEvents.push({
                timestamp: mapped.finished_at || new Date().toISOString(),
                event_type: mapped.status === 'completed' ? 'step_completed' : 'step_failed',
                step_name: '',
                detail: mapped.status === 'completed'
                  ? `Completado — costo: $${mapped.total_cost?.toFixed(3) || '0'}, tokens: ${mapped.total_tokens || 0}`
                  : (data.error_message || 'Ejecución falló'),
              })
            }
          }

          setEvents(generatedEvents)
        }
      } catch (err) {
        if (!cancelled) {
          setExecution({ run_id: runId, workflow_name: 'Error', status: 'failed', steps: [], total_cost: 0, total_tokens: 0 })
          setEvents([{ timestamp: new Date().toISOString(), event_type: 'error', step_name: '', detail: err.message || 'Failed to load execution' }])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [runId])

  // Poll for live updates when execution is still running
  useEffect(() => {
    if (!execution || execution.status === 'completed' || execution.status === 'failed') return
    const interval = setInterval(async () => {
      const res = await fetchAPI(`/executions/${runId}`)
      if (!res.error && res.data) {
        const data = res.data
        if (data.status === 'completed' || data.status === 'failed') {
          setExecution(prev => prev ? { ...prev, status: data.status, finished_at: data.completed_at } : prev)
          clearInterval(interval)
        }
      }
    }, 3000)
    return () => clearInterval(interval)
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
        <LiveLog events={events} lang={lang} />
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
