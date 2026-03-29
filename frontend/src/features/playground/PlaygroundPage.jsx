import { useState } from 'react'
import { api } from '../../services/api'
import { DEMO_ENTERPRISE_RESULT, DEMO_DOC_RESULT, DEMO_COPILOT_RESULT } from '../../services/api'

const T = {
  en: {
    title: 'Workflow Playground',
    subtitle: 'Test workflows interactively with live or demo execution.',
    selectWorkflow: 'Select Workflow',
    input: 'Input',
    sampleInputs: 'Sample Inputs',
    run: 'Run',
    running: 'Running...',
    idle: 'Idle',
    completed: 'Completed',
    failed: 'Failed',
    response: 'Response',
    timeline: 'Agent Timeline',
    metrics: 'Metrics',
    latency: 'Latency',
    agentsUsed: 'Agents Used',
    actions: 'Actions',
    demoMode: 'Demo Mode',
    noResult: 'Click "Run" to execute the workflow.',
    tokens: 'Tokens',
    cost: 'Est. Cost',
  },
  es: {
    title: 'Playground de Workflows',
    subtitle: 'Prueba workflows de forma interactiva con ejecucion real o demo.',
    selectWorkflow: 'Seleccionar Workflow',
    input: 'Entrada',
    sampleInputs: 'Entradas de Ejemplo',
    run: 'Ejecutar',
    running: 'Ejecutando...',
    idle: 'Inactivo',
    completed: 'Completado',
    failed: 'Fallido',
    response: 'Respuesta',
    timeline: 'Timeline de Agentes',
    metrics: 'Metricas',
    latency: 'Latencia',
    agentsUsed: 'Agentes Usados',
    actions: 'Acciones',
    demoMode: 'Modo Demo',
    noResult: 'Haz clic en "Ejecutar" para correr el workflow.',
    tokens: 'Tokens',
    cost: 'Costo Est.',
  },
}

const WORKFLOWS = [
  { id: 'enterprise-ops', name: 'Enterprise Ops Pipeline' },
  { id: 'document-intelligence', name: 'Document Intelligence' },
  { id: 'portfolio-copilot', name: 'Portfolio Copilot' },
]

const SAMPLES = {
  'enterprise-ops': [
    'Necesito reprogramar mi reunion del viernes y confirmar si mi contrato incluye soporte premium.',
    'I need to cancel my subscription and get a refund for the remaining months.',
    'Quiero agregar 3 usuarios nuevos a mi plan empresarial.',
  ],
  'document-intelligence': [
    'CONTRATO DE SERVICIOS PROFESIONALES - Entre Empresa ABC S.A. y Consultora XYZ. Clausula 1: Objeto del contrato. El presente contrato tiene por objeto la prestacion de servicios de consultoria...',
    'EMPLOYEE HANDBOOK - Section 4.2 Remote Work Policy. All full-time employees are eligible for up to 3 remote work days per week, subject to manager approval...',
  ],
  'portfolio-copilot': [
    'Cual proyecto demuestra mejor la orquestacion multi-agente?',
    'What are the key technical differentiators of NexusForge vs LangChain?',
    'Resume los patrones de arquitectura usados en el portfolio.',
  ],
}

const DEMO_TIMELINES = {
  'enterprise-ops': [
    { agent: 'IntakeAgent', status: 'success', latency_ms: 12 },
    { agent: 'IntentClassifierAgent', status: 'success', latency_ms: 45 },
    { agent: 'CustomerContextAgent', status: 'success', latency_ms: 23 },
    { agent: 'DocumentRAGAgent', status: 'success', latency_ms: 89 },
    { agent: 'SchedulerAgent', status: 'success', latency_ms: 15 },
    { agent: 'CRMUpdateAgent', status: 'retry', latency_ms: 234 },
    { agent: 'NotificationAgent', status: 'fallback', latency_ms: 312 },
    { agent: 'SupervisorAgent', status: 'success', latency_ms: 67 },
  ],
  'document-intelligence': [
    { agent: 'DocumentRAGAgent', status: 'success', latency_ms: 120 },
    { agent: 'SummarizerAgent', status: 'success', latency_ms: 340 },
    { agent: 'EntityExtractor', status: 'success', latency_ms: 230 },
    { agent: 'SupervisorAgent', status: 'success', latency_ms: 45 },
  ],
  'portfolio-copilot': [
    { agent: 'PortfolioAnalyzer', status: 'success', latency_ms: 450 },
    { agent: 'RiskAgent', status: 'success', latency_ms: 380 },
    { agent: 'RecommenderAgent', status: 'fallback', latency_ms: 670 },
    { agent: 'SupervisorAgent', status: 'success', latency_ms: 60 },
  ],
}

const DEMO_RESPONSES = {
  'enterprise-ops': DEMO_ENTERPRISE_RESULT,
  'document-intelligence': DEMO_DOC_RESULT,
  'portfolio-copilot': DEMO_COPILOT_RESULT,
}

const STATUS_ICONS = {
  success: { icon: '\u2714', color: '#059669' },
  retry: { icon: '\u21BB', color: '#D97706' },
  fallback: { icon: '\u26A0', color: '#D97706' },
  failure: { icon: '\u2716', color: '#DC2626' },
}

function tl(key, lang) {
  return T[lang]?.[key] || T.en[key] || key
}

export default function PlaygroundPage({ lang = 'en' }) {
  const [selectedWorkflow, setSelectedWorkflow] = useState('enterprise-ops')
  const [input, setInput] = useState(SAMPLES['enterprise-ops'][0])
  const [status, setStatus] = useState('idle') // idle | running | completed | failed
  const [result, setResult] = useState(null)
  const [isDemo, setIsDemo] = useState(false)
  const [timeline, setTimeline] = useState(null)

  const handleWorkflowChange = (wfId) => {
    setSelectedWorkflow(wfId)
    setInput(SAMPLES[wfId]?.[0] || '')
    setResult(null)
    setTimeline(null)
    setStatus('idle')
  }

  const handleRun = async () => {
    setStatus('running')
    setResult(null)
    setTimeline(null)
    setIsDemo(false)

    try {
      const { data, isDemo: demo } = await api.post(`/${selectedWorkflow}/run`, { input })
      setResult(data)
      setIsDemo(demo)
      setTimeline(DEMO_TIMELINES[selectedWorkflow] || [])
      setStatus('completed')
    } catch {
      // Fallback to demo
      setResult(DEMO_RESPONSES[selectedWorkflow])
      setIsDemo(true)
      setTimeline(DEMO_TIMELINES[selectedWorkflow] || [])
      setStatus('completed')
    }
  }

  const samples = SAMPLES[selectedWorkflow] || []

  const totalLatency = timeline ? timeline.reduce((s, t) => s + t.latency_ms, 0) : 0
  const agentsUsed = timeline ? timeline.length : 0
  const actionsCount = result?.actions_taken?.length || result?.suggested_changes?.length || result?.entities?.length || 0

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0 }}>
          {tl('title', lang)}
        </h1>
        <p style={{ fontSize: 14, color: '#6B7280', margin: '4px 0 0' }}>
          {tl('subtitle', lang)}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 24, alignItems: 'start' }}>
        {/* Left Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Workflow selector */}
          <div style={{
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20,
          }}>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              {tl('selectWorkflow', lang)}
            </label>
            <select
              value={selectedWorkflow}
              onChange={e => handleWorkflowChange(e.target.value)}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid #E5E7EB', background: '#F9FAFB',
                color: '#111827', fontSize: 14, outline: 'none', cursor: 'pointer',
              }}
            >
              {WORKFLOWS.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>

          {/* Input */}
          <div style={{
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20,
          }}>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              {tl('input', lang)}
            </label>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              rows={5}
              style={{
                width: '100%', padding: 12, borderRadius: 8,
                border: '1px solid #E5E7EB', background: '#F9FAFB',
                color: '#111827', fontSize: 14, outline: 'none', resize: 'vertical',
                fontFamily: 'inherit', lineHeight: 1.5,
                boxSizing: 'border-box',
              }}
            />

            {/* Sample buttons */}
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: 8 }}>
                {tl('sampleInputs', lang)}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {samples.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s)}
                    style={{
                      padding: '5px 10px', borderRadius: 6, border: '1px solid #E5E7EB',
                      background: input === s ? 'rgba(37,99,235,0.08)' : '#fff',
                      color: input === s ? '#2563EB' : '#6B7280',
                      fontSize: 11, cursor: 'pointer', maxWidth: '100%',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}
                  >
                    {s.slice(0, 45)}...
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Run button */}
          <button
            onClick={handleRun}
            disabled={status === 'running' || !input.trim()}
            style={{
              padding: '14px 24px', borderRadius: 10, border: 'none',
              background: status === 'running' ? '#9CA3AF' : '#2563EB',
              color: '#fff', fontSize: 15, fontWeight: 700, cursor: status === 'running' ? 'not-allowed' : 'pointer',
              transition: 'background 0.15s',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
          >
            {status === 'running' ? (
              <>
                <span style={{ display: 'inline-block', width: 16, height: 16, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'nxf-spin 0.8s linear infinite' }} />
                {tl('running', lang)}
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                {tl('run', lang)}
              </>
            )}
          </button>

          <style>{`@keyframes nxf-spin { to { transform: rotate(360deg) } }`}</style>
        </div>

        {/* Right Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Status bar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: '12px 20px',
          }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
              background: status === 'completed' ? '#ECFDF5' : status === 'failed' ? '#FEF2F2' : status === 'running' ? '#EFF6FF' : '#F3F4F6',
              color: status === 'completed' ? '#059669' : status === 'failed' ? '#DC2626' : status === 'running' ? '#2563EB' : '#6B7280',
            }}>
              {status === 'completed' && '\u2714'}
              {status === 'failed' && '\u2716'}
              {status === 'running' && '\u21BB'}
              {tl(status, lang)}
            </span>
            {isDemo && (
              <span style={{
                padding: '4px 10px', borderRadius: 20, background: '#FFFBEB',
                color: '#92400E', fontSize: 11, fontWeight: 600, border: '1px solid #FDE68A',
              }}>
                {tl('demoMode', lang)}
              </span>
            )}
          </div>

          {/* Response */}
          <div style={{
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20,
            minHeight: 200,
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: 12 }}>
              {tl('response', lang)}
            </div>
            {result ? (
              <pre style={{
                margin: 0, padding: 16, borderRadius: 8, background: '#F9FAFB',
                border: '1px solid #E5E7EB', fontSize: 13, color: '#374151',
                overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap', lineHeight: 1.6,
                fontFamily: "'SF Mono', 'Fira Code', monospace",
              }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            ) : (
              <div style={{ color: '#9CA3AF', fontSize: 14, fontStyle: 'italic', padding: 20, textAlign: 'center' }}>
                {tl('noResult', lang)}
              </div>
            )}
          </div>

          {/* Mini Timeline */}
          {timeline && timeline.length > 0 && (
            <div style={{
              background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20,
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: 12 }}>
                {tl('timeline', lang)}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {timeline.map((step, i) => {
                  const cfg = STATUS_ICONS[step.status] || STATUS_ICONS.success
                  return (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '8px 12px', borderRadius: 8,
                      borderLeft: `3px solid ${cfg.color}`, background: '#F9FAFB',
                    }}>
                      <span style={{ color: cfg.color, fontSize: 14, width: 20, textAlign: 'center' }}>{cfg.icon}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#111827', flex: 1 }}>{step.agent}</span>
                      <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#6B7280' }}>{step.latency_ms}ms</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Metrics */}
          {result && (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12,
            }}>
              {[
                { label: tl('latency', lang), value: `${totalLatency}ms`, color: '#2563EB' },
                { label: tl('agentsUsed', lang), value: agentsUsed, color: '#7C3AED' },
                { label: tl('actions', lang), value: actionsCount, color: '#059669' },
              ].map((m, i) => (
                <div key={i} style={{
                  background: '#fff', borderRadius: 10, border: '1px solid #E5E7EB',
                  padding: 16, textAlign: 'center',
                }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', marginTop: 2 }}>{m.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
