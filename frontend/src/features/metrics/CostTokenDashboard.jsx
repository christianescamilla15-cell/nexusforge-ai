import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const T = {
  en: {
    title: 'Cost & Token Metrics',
    subtitle: 'Monitor resource consumption, costs, and reliability across all runs.',
    totalTokens: 'Total Tokens',
    totalCost: 'Total Cost (USD)',
    avgLatency: 'Avg Latency',
    retryCount: 'Total Retries',
    fallbackCount: 'Total Fallbacks',
    successRate: 'Success Rate',
    perRunTable: 'Per-Run Breakdown',
    perAgentTable: 'Per-Agent Breakdown',
    run: 'Run',
    workflow: 'Workflow',
    duration: 'Duration',
    tokens: 'Tokens',
    cost: 'Cost',
    status: 'Status',
    agent: 'Agent',
    executions: 'Executions',
    avgLat: 'Avg Latency',
    retries: 'Retries',
    fallbacks: 'Fallbacks',
    demoMode: 'Demo Mode',
    completed: 'Completed',
    failed: 'Failed',
    loading: 'Loading...',
  },
  es: {
    title: 'Metricas de Costos y Tokens',
    subtitle: 'Monitorea consumo de recursos, costos y confiabilidad en todas las ejecuciones.',
    totalTokens: 'Tokens Totales',
    totalCost: 'Costo Total (USD)',
    avgLatency: 'Latencia Prom.',
    retryCount: 'Total Reintentos',
    fallbackCount: 'Total Fallbacks',
    successRate: 'Tasa de Exito',
    perRunTable: 'Desglose por Ejecucion',
    perAgentTable: 'Desglose por Agente',
    run: 'Ejecucion',
    workflow: 'Workflow',
    duration: 'Duracion',
    tokens: 'Tokens',
    cost: 'Costo',
    status: 'Estado',
    agent: 'Agente',
    executions: 'Ejecuciones',
    avgLat: 'Latencia Prom.',
    retries: 'Reintentos',
    fallbacks: 'Fallbacks',
    demoMode: 'Modo Demo',
    completed: 'Completado',
    failed: 'Fallido',
    loading: 'Cargando...',
  },
}

const DEMO_RUNS = [
  { id: 'run-001', workflow: 'Enterprise Ops Pipeline', duration_ms: 797, tokens: 845, cost: 0.0025, status: 'completed' },
  { id: 'run-002', workflow: 'Document Intelligence', duration_ms: 735, tokens: 520, cost: 0.0016, status: 'completed' },
  { id: 'run-003', workflow: 'Portfolio Copilot', duration_ms: 1560, tokens: 1200, cost: 0.0036, status: 'completed' },
  { id: 'run-004', workflow: 'Enterprise Ops Pipeline', duration_ms: 4500, tokens: 300, cost: 0.0009, status: 'failed' },
  { id: 'run-005', workflow: 'Document Intelligence', duration_ms: 640, tokens: 480, cost: 0.0014, status: 'completed' },
  { id: 'run-006', workflow: 'Enterprise Ops Pipeline', duration_ms: 920, tokens: 910, cost: 0.0027, status: 'completed' },
  { id: 'run-007', workflow: 'Portfolio Copilot', duration_ms: 1780, tokens: 1350, cost: 0.0041, status: 'completed' },
  { id: 'run-008', workflow: 'Enterprise Ops Pipeline', duration_ms: 1100, tokens: 870, cost: 0.0026, status: 'completed' },
]

const DEMO_AGENTS = [
  { agent: 'IntakeAgent', executions: 47, avg_latency_ms: 14, tokens: 0, retries: 0, fallbacks: 0 },
  { agent: 'IntentClassifierAgent', executions: 47, avg_latency_ms: 52, tokens: 7050, retries: 0, fallbacks: 0 },
  { agent: 'CustomerContextAgent', executions: 38, avg_latency_ms: 28, tokens: 0, retries: 1, fallbacks: 0 },
  { agent: 'DocumentRAGAgent', executions: 32, avg_latency_ms: 95, tokens: 10240, retries: 2, fallbacks: 0 },
  { agent: 'SchedulerAgent', executions: 15, avg_latency_ms: 18, tokens: 0, retries: 0, fallbacks: 0 },
  { agent: 'CRMUpdateAgent', executions: 28, avg_latency_ms: 180, tokens: 2240, retries: 5, fallbacks: 0 },
  { agent: 'NotificationAgent', executions: 22, avg_latency_ms: 290, tokens: 2090, retries: 1, fallbacks: 3 },
  { agent: 'SupervisorAgent', executions: 47, avg_latency_ms: 70, tokens: 9400, retries: 0, fallbacks: 0 },
  { agent: 'SummarizerAgent', executions: 18, avg_latency_ms: 340, tokens: 6120, retries: 0, fallbacks: 1 },
  { agent: 'PortfolioAnalyzer', executions: 12, avg_latency_ms: 450, tokens: 5400, retries: 0, fallbacks: 0 },
  { agent: 'RiskAgent', executions: 12, avg_latency_ms: 380, tokens: 4560, retries: 1, fallbacks: 0 },
  { agent: 'RecommenderAgent', executions: 12, avg_latency_ms: 520, tokens: 6240, retries: 0, fallbacks: 2 },
]

function tl(key, lang) {
  return T[lang]?.[key] || T.en[key] || key
}

export default function CostTokenDashboard({ lang = 'en' }) {
  const [runs, setRuns] = useState(DEMO_RUNS)
  const [agents, setAgents] = useState(DEMO_AGENTS)
  const [isDemo, setIsDemo] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const { data, isDemo: demo } = await fetchAPI('/reliability/health')
        if (!demo && data.agents) {
          setAgents(data.agents.map(a => ({
            agent: a.agent,
            executions: a.executions || 0,
            avg_latency_ms: a.avg_latency_ms || 0,
            tokens: a.tokens || 0,
            retries: a.retries || 0,
            fallbacks: a.fallbacks || 0,
          })))
          setIsDemo(false)
        }
        const runsRes = await fetchAPI('/runs')
        if (!runsRes.isDemo && runsRes.data?.runs) {
          setRuns(runsRes.data.runs.map(r => ({
            id: r.id,
            workflow: r.workflow_name,
            duration_ms: r.latency_ms,
            tokens: r.tokens || Math.round(r.latency_ms * 0.5),
            cost: r.cost || (r.latency_ms * 0.5 * 0.000003),
            status: r.status,
          })))
          setIsDemo(false)
        }
      } catch {
        // keep demo data
      }
      setLoading(false)
    }
    load()
  }, [])

  const totalTokens = runs.reduce((s, r) => s + r.tokens, 0)
  const totalCost = runs.reduce((s, r) => s + r.cost, 0)
  const avgLatency = Math.round(runs.reduce((s, r) => s + r.duration_ms, 0) / runs.length)
  const totalRetries = agents.reduce((s, a) => s + a.retries, 0)
  const totalFallbacks = agents.reduce((s, a) => s + a.fallbacks, 0)
  const successCount = runs.filter(r => r.status === 'completed').length
  const successRate = ((successCount / runs.length) * 100).toFixed(1)

  const kpis = [
    { label: tl('totalTokens', lang), value: totalTokens.toLocaleString(), color: '#2563EB' },
    { label: tl('totalCost', lang), value: `$${totalCost.toFixed(4)}`, color: '#7C3AED' },
    { label: tl('avgLatency', lang), value: `${avgLatency}ms`, color: '#0891B2' },
    { label: tl('retryCount', lang), value: totalRetries, color: '#D97706' },
    { label: tl('fallbackCount', lang), value: totalFallbacks, color: '#D97706' },
    { label: tl('successRate', lang), value: `${successRate}%`, color: '#059669' },
  ]

  const thStyle = {
    padding: '10px 14px', fontSize: 11, fontWeight: 700, color: '#6B7280',
    textTransform: 'uppercase', textAlign: 'left', borderBottom: '1px solid #E5E7EB',
    background: '#F9FAFB',
  }
  const tdStyle = {
    padding: '10px 14px', fontSize: 13, color: '#374151',
    borderBottom: '1px solid #F3F4F6',
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: '#6B7280' }}>
        {tl('loading', lang)}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0 }}>
            {tl('title', lang)}
          </h1>
          {isDemo && (
            <span style={{
              padding: '4px 12px', borderRadius: 20, background: '#FFFBEB',
              color: '#92400E', fontSize: 11, fontWeight: 600, border: '1px solid #FDE68A',
            }}>
              {tl('demoMode', lang)}
            </span>
          )}
        </div>
        <p style={{ fontSize: 14, color: '#6B7280', margin: '4px 0 0' }}>
          {tl('subtitle', lang)}
        </p>
      </div>

      {/* KPI Cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: 16, marginBottom: 32,
      }}>
        {kpis.map((kpi, i) => (
          <div key={i} style={{
            background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
            padding: 20, textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', marginTop: 6 }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* Per-Run Table */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        overflow: 'hidden', marginBottom: 24,
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB' }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>
            {tl('perRunTable', lang)}
          </h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>{tl('run', lang)}</th>
                <th style={thStyle}>{tl('workflow', lang)}</th>
                <th style={thStyle}>{tl('duration', lang)}</th>
                <th style={thStyle}>{tl('tokens', lang)}</th>
                <th style={thStyle}>{tl('cost', lang)}</th>
                <th style={thStyle}>{tl('status', lang)}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => (
                <tr key={i} style={{ transition: 'background 0.1s' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{r.id}</td>
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{r.workflow}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{(r.duration_ms / 1000).toFixed(2)}s</td>
                  <td style={tdStyle}>{r.tokens.toLocaleString()}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace' }}>${r.cost.toFixed(4)}</td>
                  <td style={tdStyle}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                      background: r.status === 'completed' ? '#ECFDF5' : '#FEF2F2',
                      color: r.status === 'completed' ? '#059669' : '#DC2626',
                    }}>
                      {r.status === 'completed' ? '\u2714' : '\u2716'} {tl(r.status, lang)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-Agent Table */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB' }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#111827' }}>
            {tl('perAgentTable', lang)}
          </h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>{tl('agent', lang)}</th>
                <th style={thStyle}>{tl('executions', lang)}</th>
                <th style={thStyle}>{tl('avgLat', lang)}</th>
                <th style={thStyle}>{tl('tokens', lang)}</th>
                <th style={thStyle}>{tl('retries', lang)}</th>
                <th style={thStyle}>{tl('fallbacks', lang)}</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a, i) => (
                <tr key={i} style={{ transition: 'background 0.1s' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{a.agent}</td>
                  <td style={tdStyle}>{a.executions}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{a.avg_latency_ms}ms</td>
                  <td style={tdStyle}>{a.tokens.toLocaleString()}</td>
                  <td style={tdStyle}>
                    {a.retries > 0 ? (
                      <span style={{ color: '#D97706', fontWeight: 600 }}>{a.retries}</span>
                    ) : (
                      <span style={{ color: '#D1D5DB' }}>0</span>
                    )}
                  </td>
                  <td style={tdStyle}>
                    {a.fallbacks > 0 ? (
                      <span style={{ color: '#D97706', fontWeight: 600 }}>{a.fallbacks}</span>
                    ) : (
                      <span style={{ color: '#D1D5DB' }}>0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
