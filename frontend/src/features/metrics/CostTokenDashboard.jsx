import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'

const T = {
  en: {
    title: 'Cost & Token Metrics',
    subtitle: 'Monitor resource consumption, costs, and reliability across all runs.',
    totalTokens: 'Total Tokens',
    totalCost: 'Total Cost (USD)',
    noLlm: 'No LLM usage — agents using rule-based logic (set GROQ_API_KEY to enable)',
    provider: 'Provider',
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
    noLlm: 'Sin uso de LLM — agentes usando logica basada en reglas (configura GROQ_API_KEY para activar)',
    provider: 'Proveedor',
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

function tl(key, lang) {
  return T[lang]?.[key] || T.en[key] || key
}

export default function CostTokenDashboard({ lang = 'en', embedded = false }) {
  const [runs, setRuns] = useState([])
  const [agents, setAgents] = useState([])
  const [isDemo, setIsDemo] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [providerStatus, setProviderStatus] = useState(null)

  useEffect(() => {
    async function load() {
      const [healthRes, runsRes] = await Promise.all([
        fetchAPI('/runs/reliability/health'),
        fetchAPI('/runs/'),
      ])

      if (healthRes.error || runsRes.error) {
        setError(healthRes.error || runsRes.error)
        setLoading(false)
        return
      }

      setIsDemo(healthRes.isDemo || runsRes.isDemo)

      if (healthRes.data?.agents) {
        setAgents(healthRes.data.agents.map(a => ({
          agent: a.agent,
          executions: a.executions || 0,
          avg_latency_ms: a.avg_latency_ms || 0,
          tokens: a.tokens || 0,
          retries: a.retries || 0,
          fallbacks: a.fallbacks || 0,
        })))
      }

      if (runsRes.data?.runs) {
        setRuns(runsRes.data.runs.map(r => ({
          id: r.id,
          workflow: r.workflow_name,
          duration_ms: r.total_latency_ms || r.latency_ms || 0,
          tokens: r.total_tokens || r.tokens || 0,
          cost: r.total_cost || r.cost || 0,
          status: r.status,
        })))
      }

      const provRes = await fetchAPI('/providers/status')
      if (!provRes.error && provRes.data) {
        setProviderStatus(provRes.data)
      }

      setLoading(false)
    }
    load()
  }, [])

  const totalTokens = runs.reduce((s, r) => s + (r.tokens || 0), 0)
  const totalCost = runs.reduce((s, r) => s + (r.cost || 0), 0)
  const avgLatency = runs.length > 0 ? Math.round(runs.reduce((s, r) => s + (r.duration_ms || 0), 0) / runs.length) : 0
  const totalRetries = agents.reduce((s, a) => s + (a.retries || 0), 0)
  const totalFallbacks = agents.reduce((s, a) => s + (a.fallbacks || 0), 0)
  const successCount = runs.filter(r => r.status === 'completed').length
  const successRate = runs.length > 0 ? ((successCount / runs.length) * 100).toFixed(1) : '0.0'

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
      {/* Header — hidden when embedded */}
      {!embedded && <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0 }}>
            {tl('title', lang)}
          </h1>
        </div>
        <p style={{ fontSize: 14, color: '#6B7280', margin: '4px 0 0' }}>
          {tl('subtitle', lang)}
        </p>
      </div>}

      {/* Error banner for Real mode failures */}
      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
          color: '#991B1B', fontSize: 14, lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <span style={{ flexShrink: 0, fontSize: 16 }}>{'\u274C'}</span>
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

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

      {/* No LLM info banner */}
      {!isDemo && totalTokens === 0 && providerStatus && providerStatus.active_provider === 'none' && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(37,99,235,0.06)', border: '1px solid rgba(37,99,235,0.2)',
          color: '#1E40AF', fontSize: 14, lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <span style={{ flexShrink: 0, fontSize: 16 }}>{'\u2139\uFE0F'}</span>
          <div>{tl('noLlm', lang)}</div>
        </div>
      )}

      {/* Active provider badge */}
      {providerStatus && providerStatus.active_provider !== 'none' && (
        <div style={{
          padding: '10px 16px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(5,150,105,0.06)', border: '1px solid rgba(5,150,105,0.2)',
          color: '#065F46', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#059669', display: 'inline-block' }} />
          <span><strong>{tl('provider', lang)}:</strong> {providerStatus.active_provider} ({providerStatus[providerStatus.active_provider]?.model || 'unknown'})</span>
        </div>
      )}

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
