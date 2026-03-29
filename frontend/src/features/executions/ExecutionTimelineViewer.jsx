import { useState } from 'react'
import { t } from '../../shared/i18n/translations'

const DEMO_TIMELINE = [
  { offset: '00:00', agent: 'IntakeAgent', status: 'success', latency_ms: 12, tokens: 0, input: '{ "channel": "email", "message": "Necesito reprogramar mi reunion..." }', output: 'Message received, forwarding to classifier' },
  { offset: '00:01', agent: 'IntentClassifierAgent', status: 'success', latency_ms: 45, tokens: 150, provider: 'Claude 3.5', input: '{ "text": "Necesito reprogramar mi reunion del viernes..." }', output: 'reschedule_meeting (92%)' },
  { offset: '00:02', agent: 'CustomerContextAgent', status: 'success', latency_ms: 23, tokens: 0, input: '{ "email": "maria.gonzalez@enterprise.com" }', output: 'Maria Gonzalez - Enterprise (CUST-042)' },
  { offset: '00:03', agent: 'DocumentRAGAgent', status: 'success', latency_ms: 89, tokens: 320, provider: 'Claude 3.5', input: '{ "query": "reschedule policy", "customer_tier": "enterprise" }', output: '1 policy retrieved: scheduling-policy.md' },
  { offset: '00:04', agent: 'SchedulerAgent', status: 'success', latency_ms: 15, tokens: 0, input: '{ "action": "reschedule", "original": "2026-03-28 15:00" }', output: '2026-04-01 09:00 selected' },
  { offset: '00:05', agent: 'CRMUpdateAgent', status: 'retry', latency_ms: 234, tokens: 80, retries: 1, provider: 'Groq', input: '{ "customer_id": "CUST-042", "action": "log_interaction" }', output: 'CRM updated (retry 1 - initial timeout)' },
  { offset: '00:06', agent: 'NotificationAgent', status: 'fallback', latency_ms: 312, tokens: 95, fallback: 'Groq -> Claude', provider: 'Claude 3.5 (fallback)', input: '{ "channels": ["slack", "email"], "message": "Meeting rescheduled" }', output: 'Team notified via Slack + email' },
  { offset: '00:07', agent: 'SupervisorAgent', status: 'success', latency_ms: 67, tokens: 200, provider: 'Claude 3.5', input: '{ "pipeline_result": { "status": "all_steps_ok", "actions": 6 } }', output: 'Response approved - quality score 0.96' },
]

const STATUS_CONFIG = {
  success:  { icon: '\u2714', color: '#059669', bg: '#ECFDF5', label: { en: 'Success', es: 'Exitoso' } },
  retry:    { icon: '\u21BB', color: '#D97706', bg: '#FFFBEB', label: { en: 'Retry',   es: 'Reintento' } },
  fallback: { icon: '\u26A0', color: '#D97706', bg: '#FFFBEB', label: { en: 'Fallback', es: 'Fallback' } },
  failure:  { icon: '\u2716', color: '#DC2626', bg: '#FEF2F2', label: { en: 'Failed',  es: 'Fallido' } },
}

const T = {
  en: {
    runHeader: 'Execution Timeline',
    workflow: 'Workflow',
    status: 'Status',
    duration: 'Duration',
    totalTokens: 'Total Tokens',
    estimatedCost: 'Est. Cost',
    step: 'Step',
    time: 'Time',
    agent: 'Agent',
    latency: 'Latency',
    detail: 'Detail',
    input: 'Input',
    output: 'Output',
    tokens: 'Tokens',
    retries: 'Retries',
    provider: 'Provider',
    fallbackFrom: 'Fallback',
    summary: 'Summary',
    totalSteps: 'Total Steps',
    successRate: 'Success Rate',
    fallbackCount: 'Fallbacks',
    retryCount: 'Retries',
    demoMode: 'Demo Mode',
    completed: 'Completed',
  },
  es: {
    runHeader: 'Timeline de Ejecucion',
    workflow: 'Workflow',
    status: 'Estado',
    duration: 'Duracion',
    totalTokens: 'Tokens Totales',
    estimatedCost: 'Costo Est.',
    step: 'Paso',
    time: 'Tiempo',
    agent: 'Agente',
    latency: 'Latencia',
    detail: 'Detalle',
    input: 'Entrada',
    output: 'Salida',
    tokens: 'Tokens',
    retries: 'Reintentos',
    provider: 'Proveedor',
    fallbackFrom: 'Fallback',
    summary: 'Resumen',
    totalSteps: 'Total Pasos',
    successRate: 'Tasa de Exito',
    fallbackCount: 'Fallbacks',
    retryCount: 'Reintentos',
    demoMode: 'Modo Demo',
    completed: 'Completado',
  },
}

function tl(key, lang) {
  return T[lang]?.[key] || T.en[key] || key
}

export default function ExecutionTimelineViewer({ lang = 'en', timeline, runMeta }) {
  const [expanded, setExpanded] = useState({})
  const steps = timeline || DEMO_TIMELINE
  const isDemo = !timeline

  const meta = runMeta || {
    workflow: 'Enterprise Ops Pipeline',
    status: 'completed',
    duration_ms: steps.reduce((s, st) => s + st.latency_ms, 0),
    total_tokens: steps.reduce((s, st) => s + (st.tokens || 0), 0),
  }

  const costEstimate = (meta.total_tokens * 0.000003).toFixed(4)
  const successCount = steps.filter(s => s.status === 'success').length
  const retryCount = steps.filter(s => s.status === 'retry').length
  const fallbackCount = steps.filter(s => s.status === 'fallback').length
  const successRate = ((successCount / steps.length) * 100).toFixed(0)

  const toggleExpand = (i) => setExpanded(p => ({ ...p, [i]: !p[i] }))

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* Demo badge */}
      {isDemo && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 12px', borderRadius: 20, background: '#FFFBEB',
          color: '#92400E', fontSize: 12, fontWeight: 600, marginBottom: 16,
          border: '1px solid #FDE68A',
        }}>
          <span style={{ fontSize: 14 }}>{'\u26A0'}</span> {tl('demoMode', lang)}
        </div>
      )}

      {/* Run Header Card */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: 24, marginBottom: 24,
      }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 20, fontWeight: 700, color: '#111827' }}>
          {tl('runHeader', lang)}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16 }}>
          {[
            { label: tl('workflow', lang), value: meta.workflow },
            { label: tl('status', lang), value: (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                background: meta.status === 'completed' ? '#ECFDF5' : '#FEF2F2',
                color: meta.status === 'completed' ? '#059669' : '#DC2626',
              }}>
                {meta.status === 'completed' ? '\u2714' : '\u2716'} {tl('completed', lang)}
              </span>
            )},
            { label: tl('duration', lang), value: `${(meta.duration_ms / 1000).toFixed(2)}s` },
            { label: tl('totalTokens', lang), value: meta.total_tokens.toLocaleString() },
            { label: tl('estimatedCost', lang), value: `$${costEstimate}` },
          ].map((item, i) => (
            <div key={i}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', marginBottom: 4 }}>
                {item.label}
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline Steps */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        overflow: 'hidden', overflowX: 'auto', WebkitOverflowScrolling: 'touch',
      }}>
        {/* Header row */}
        <div style={{
          display: 'grid', gridTemplateColumns: '60px 36px 1fr 80px 40px',
          gap: 12, padding: '12px 20px', borderBottom: '1px solid #E5E7EB',
          background: '#F9FAFB', fontSize: 11, fontWeight: 700, color: '#6B7280',
          textTransform: 'uppercase',
        }}>
          <span>{tl('time', lang)}</span>
          <span></span>
          <span>{tl('agent', lang)}</span>
          <span>{tl('latency', lang)}</span>
          <span></span>
        </div>

        {steps.map((step, i) => {
          const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.success
          const isOpen = expanded[i]
          return (
            <div key={i}>
              {/* Step row */}
              <div
                onClick={() => toggleExpand(i)}
                style={{
                  display: 'grid', gridTemplateColumns: '60px 36px 1fr 80px 40px',
                  gap: 12, padding: '14px 20px', cursor: 'pointer',
                  borderBottom: '1px solid #F3F4F6',
                  borderLeft: `3px solid ${cfg.color}`,
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{ fontFamily: 'monospace', fontSize: 13, color: '#6B7280' }}>
                  {step.offset}
                </span>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  width: 28, height: 28, borderRadius: '50%',
                  background: cfg.bg, color: cfg.color,
                  fontSize: 14, fontWeight: 700,
                }}>
                  {cfg.icon}
                </span>
                <div>
                  <span style={{ fontWeight: 600, color: '#111827', fontSize: 14 }}>
                    {step.agent}
                  </span>
                  {step.output && (
                    <span style={{ marginLeft: 8, fontSize: 12, color: '#6B7280' }}>
                      {step.output.length > 50 ? step.output.slice(0, 50) + '...' : step.output}
                    </span>
                  )}
                </div>
                <span style={{ fontFamily: 'monospace', fontSize: 13, color: '#374151' }}>
                  {step.latency_ms}ms
                </span>
                <span style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#9CA3AF', fontSize: 16,
                  transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                }}>
                  {'\u25BC'}
                </span>
              </div>

              {/* Expanded detail */}
              {isOpen && (
                <div style={{
                  padding: '16px 20px 16px 32px',
                  background: '#F9FAFB', borderBottom: '1px solid #E5E7EB',
                  display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
                }}>
                  {step.input && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: 6 }}>
                        {tl('input', lang)}
                      </div>
                      <pre style={{
                        margin: 0, padding: 12, borderRadius: 8, background: '#fff',
                        border: '1px solid #E5E7EB', fontSize: 12, color: '#374151',
                        overflow: 'auto', maxHeight: 120, whiteSpace: 'pre-wrap',
                        fontFamily: "'SF Mono', 'Fira Code', monospace",
                      }}>
                        {step.input}
                      </pre>
                    </div>
                  )}
                  {step.output && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: 6 }}>
                        {tl('output', lang)}
                      </div>
                      <pre style={{
                        margin: 0, padding: 12, borderRadius: 8, background: '#fff',
                        border: '1px solid #E5E7EB', fontSize: 12, color: '#374151',
                        overflow: 'auto', maxHeight: 120, whiteSpace: 'pre-wrap',
                        fontFamily: "'SF Mono', 'Fira Code', monospace",
                      }}>
                        {step.output}
                      </pre>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 24, gridColumn: '1 / -1' }}>
                    {step.tokens > 0 && (
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#6B7280' }}>{tl('tokens', lang)}: </span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{step.tokens}</span>
                      </div>
                    )}
                    {step.retries > 0 && (
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#D97706' }}>{tl('retries', lang)}: </span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#D97706' }}>{step.retries}</span>
                      </div>
                    )}
                    {step.fallback && (
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#D97706' }}>{tl('fallbackFrom', lang)}: </span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#D97706' }}>{step.fallback}</span>
                      </div>
                    )}
                    {step.provider && (
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#6B7280' }}>{tl('provider', lang)}: </span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{step.provider}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Summary Footer */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(140px, 100%), 1fr))', gap: 16, marginTop: 24,
      }}>
        {[
          { label: tl('totalSteps', lang), value: steps.length, color: '#2563EB' },
          { label: tl('successRate', lang), value: `${successRate}%`, color: '#059669' },
          { label: tl('retryCount', lang), value: retryCount, color: '#D97706' },
          { label: tl('fallbackCount', lang), value: fallbackCount, color: '#D97706' },
        ].map((m, i) => (
          <div key={i} style={{
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
            padding: 20, textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: m.color }}>{m.value}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', marginTop: 4 }}>{m.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
