import { useState, useCallback } from 'react'
import { t } from '../../shared/i18n/translations'

const DEMO_EVAL_RESULTS = {
  total_scenarios: 16,
  passed: 14,
  failed: 2,
  pass_rate: 0.875,
  avg_latency_ms: 156,
  avg_quality_score: 0.91,
  suites: [
    { name: 'Enterprise Operations', scenarios: 4, passed: 4, avg_latency: 89 },
    { name: 'Document Intelligence', scenarios: 6, passed: 5, avg_latency: 134 },
    { name: 'Portfolio Copilot', scenarios: 6, passed: 5, avg_latency: 245 },
  ],
  details: [
    { scenario: 'reschedule_meeting_es', suite: 'Enterprise Ops', status: 'passed', latency: 78, quality: 0.95, tokens: 1240, fallback: false },
    { scenario: 'verify_contract_en', suite: 'Enterprise Ops', status: 'passed', latency: 92, quality: 0.93, tokens: 1580, fallback: false },
    { scenario: 'approve_expense_es', suite: 'Enterprise Ops', status: 'passed', latency: 85, quality: 0.91, tokens: 980, fallback: false },
    { scenario: 'onboard_employee_en', suite: 'Enterprise Ops', status: 'passed', latency: 102, quality: 0.89, tokens: 2100, fallback: true },
    { scenario: 'contract_extraction_es', suite: 'Document Intel', status: 'passed', latency: 112, quality: 0.97, tokens: 2450, fallback: false },
    { scenario: 'invoice_processing_en', suite: 'Document Intel', status: 'passed', latency: 98, quality: 0.94, tokens: 1820, fallback: false },
    { scenario: 'resume_parsing_es', suite: 'Document Intel', status: 'passed', latency: 145, quality: 0.92, tokens: 1960, fallback: false },
    { scenario: 'malformed_document', suite: 'Document Intel', status: 'failed', latency: 45, quality: 0.30, tokens: 680, fallback: true },
    { scenario: 'multilingual_doc_en', suite: 'Document Intel', status: 'passed', latency: 167, quality: 0.88, tokens: 3200, fallback: false },
    { scenario: 'scanned_pdf_ocr', suite: 'Document Intel', status: 'passed', latency: 238, quality: 0.85, tokens: 2800, fallback: false },
    { scenario: 'best_for_orchestration', suite: 'Portfolio Copilot', status: 'passed', latency: 201, quality: 0.94, tokens: 1650, fallback: false },
    { scenario: 'compare_projects', suite: 'Portfolio Copilot', status: 'passed', latency: 289, quality: 0.88, tokens: 2340, fallback: false },
    { scenario: 'explain_architecture', suite: 'Portfolio Copilot', status: 'passed', latency: 312, quality: 0.91, tokens: 2780, fallback: false },
    { scenario: 'recommend_agent_stack', suite: 'Portfolio Copilot', status: 'passed', latency: 198, quality: 0.93, tokens: 1420, fallback: false },
    { scenario: 'adversarial_prompt', suite: 'Portfolio Copilot', status: 'failed', latency: 156, quality: 0.42, tokens: 890, fallback: true },
    { scenario: 'portfolio_summary_es', suite: 'Portfolio Copilot', status: 'passed', latency: 315, quality: 0.90, tokens: 2960, fallback: false },
  ],
}

const SUITE_COLORS = {
  'Enterprise Operations': '#2563EB',
  'Document Intelligence': '#10B981',
  'Portfolio Copilot': '#8B5CF6',
}

const SUITE_ICONS = {
  'Enterprise Operations': 'M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21',
  'Document Intelligence': 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  'Portfolio Copilot': 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z',
}

export default function EvaluationPage({ lang = 'en' }) {
  const [results, setResults] = useState(DEMO_EVAL_RESULTS)
  const [running, setRunning] = useState(false)
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('scenario')
  const [runHistory, setRunHistory] = useState([
    { id: 1, timestamp: '2026-03-29 14:32', pass_rate: 0.875, avg_latency: 156, avg_quality: 0.91 },
    { id: 2, timestamp: '2026-03-28 10:15', pass_rate: 0.812, avg_latency: 178, avg_quality: 0.87 },
    { id: 3, timestamp: '2026-03-27 16:45', pass_rate: 0.75, avg_latency: 203, avg_quality: 0.84 },
  ])

  const runEvaluation = useCallback(() => {
    if (running) return
    setRunning(true)
    setTimeout(() => {
      const newResults = { ...DEMO_EVAL_RESULTS }
      newResults.details = newResults.details.map(d => ({
        ...d,
        latency: Math.round(d.latency * (0.85 + Math.random() * 0.3)),
        quality: Math.min(1, +(d.quality * (0.95 + Math.random() * 0.1)).toFixed(2)),
      }))
      const passed = newResults.details.filter(d => d.quality >= 0.6).length
      newResults.passed = passed
      newResults.failed = newResults.total_scenarios - passed
      newResults.pass_rate = +(passed / newResults.total_scenarios).toFixed(3)
      newResults.avg_latency_ms = Math.round(newResults.details.reduce((s, d) => s + d.latency, 0) / newResults.details.length)
      newResults.avg_quality_score = +(newResults.details.reduce((s, d) => s + d.quality, 0) / newResults.details.length).toFixed(2)

      newResults.suites = newResults.suites.map(suite => {
        const suiteDetails = newResults.details.filter(d => d.suite.startsWith(suite.name.split(' ')[0]))
        return {
          ...suite,
          passed: suiteDetails.filter(d => d.quality >= 0.6).length,
          avg_latency: Math.round(suiteDetails.reduce((s, d) => s + d.latency, 0) / suiteDetails.length),
        }
      })

      setResults(newResults)
      const now = new Date()
      setRunHistory(prev => [{
        id: prev.length + 1,
        timestamp: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`,
        pass_rate: newResults.pass_rate,
        avg_latency: newResults.avg_latency_ms,
        avg_quality: newResults.avg_quality_score,
      }, ...prev])
      setRunning(false)
    }, 2500)
  }, [running])

  const filteredDetails = results.details
    .filter(d => filter === 'all' || (filter === 'passed' && d.status === 'passed') || (filter === 'failed' && d.status === 'failed'))
    .sort((a, b) => {
      if (sortBy === 'latency') return a.latency - b.latency
      if (sortBy === 'quality') return b.quality - a.quality
      return a.scenario.localeCompare(b.scenario)
    })

  const fallbackRate = +(results.details.filter(d => d.fallback).length / results.details.length * 100).toFixed(1)

  const isEs = lang === 'es'

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
            {isEs ? 'Escenarios de Evaluacion' : 'Evaluation Scenarios'}
          </h1>
          <p style={{ fontSize: 14, color: '#9CA3AF', margin: 0 }}>
            {isEs
              ? 'Ejecuta evaluaciones automatizadas en los 3 casos de uso. 16 escenarios de prueba con metricas de calidad, latencia y tasa de fallback.'
              : 'Run automated evaluations across 3 use cases. 16 test scenarios with quality, latency, and fallback metrics.'
            }
          </p>
        </div>
        <button
          onClick={runEvaluation}
          disabled={running}
          style={{
            padding: '10px 24px', borderRadius: 10, border: 'none',
            background: running ? '#9CA3AF' : 'linear-gradient(135deg, #2563EB, #1D4ED8)',
            color: '#fff', fontSize: 14, fontWeight: 600, cursor: running ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: 8,
            boxShadow: running ? 'none' : '0 2px 8px rgba(37,99,235,0.3)',
          }}
          onMouseEnter={(e) => !running && (e.currentTarget.style.transform = 'translateY(-1px)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
        >
          {running && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
              <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.49-8.49l2.83-2.83M2 12h4m12 0h4m-3.93 7.07l-2.83-2.83M7.76 7.76L4.93 4.93" />
            </svg>
          )}
          {running
            ? (isEs ? 'Ejecutando...' : 'Running...')
            : (isEs ? 'Ejecutar Evaluacion' : 'Run Evaluation')
          }
        </button>
      </div>

      {/* Suite Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
        {results.suites.map((suite) => {
          const color = SUITE_COLORS[suite.name] || '#6B7280'
          const icon = SUITE_ICONS[suite.name]
          const pct = suite.scenarios > 0 ? Math.round((suite.passed / suite.scenarios) * 100) : 0
          return (
            <div key={suite.name} style={{
              background: '#FFFFFF', borderRadius: 14, padding: 20,
              border: `1px solid ${color}22`, transition: 'all 0.2s',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  background: `${color}12`,
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d={icon} />
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{suite.name}</div>
                  <div style={{ fontSize: 12, color: '#9CA3AF' }}>
                    {suite.scenarios} {isEs ? 'escenarios' : 'scenarios'}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 16 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600 }}>
                    {isEs ? 'Aprobados' : 'Passed'}
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: pct === 100 ? '#10B981' : pct >= 80 ? '#F59E0B' : '#EF4444' }}>
                    {suite.passed}/{suite.scenarios}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600 }}>
                    {isEs ? 'Tasa' : 'Rate'}
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#111827' }}>{pct}%</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600 }}>
                    {isEs ? 'Latencia' : 'Latency'}
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#111827' }}>{suite.avg_latency}ms</div>
                </div>
              </div>
              {/* Progress bar */}
              <div style={{ marginTop: 12, height: 4, borderRadius: 2, background: '#E5E7EB', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${pct}%`, borderRadius: 2,
                  background: pct === 100 ? '#10B981' : pct >= 80 ? '#F59E0B' : '#EF4444',
                  transition: 'width 0.5s ease',
                }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* KPI Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: isEs ? 'Escenarios' : 'Scenarios', value: results.total_scenarios, color: '#2563EB' },
          { label: isEs ? 'Tasa Aprobacion' : 'Pass Rate', value: `${(results.pass_rate * 100).toFixed(1)}%`, color: results.pass_rate >= 0.85 ? '#10B981' : '#F59E0B' },
          { label: isEs ? 'Latencia Prom.' : 'Avg Latency', value: `${results.avg_latency_ms}ms`, color: '#6366F1' },
          { label: isEs ? 'Calidad Prom.' : 'Avg Quality', value: results.avg_quality_score.toFixed(2), color: '#8B5CF6' },
          { label: isEs ? 'Tasa Fallback' : 'Fallback Rate', value: `${fallbackRate}%`, color: fallbackRate > 20 ? '#EF4444' : '#10B981' },
          { label: isEs ? 'Fallidos' : 'Failed', value: results.failed, color: results.failed > 0 ? '#EF4444' : '#10B981' },
        ].map((kpi) => (
          <div key={kpi.label} style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB', textAlign: 'center',
          }}>
            <div style={{ fontSize: 11, color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600, marginBottom: 6 }}>{kpi.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 16, flexWrap: 'wrap', gap: 12,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#111827', margin: 0 }}>
          {isEs ? 'Resultados por Escenario' : 'Per-Scenario Results'}
        </h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {[
            { key: 'all', label: isEs ? 'Todos' : 'All' },
            { key: 'passed', label: isEs ? 'Aprobados' : 'Passed' },
            { key: 'failed', label: isEs ? 'Fallidos' : 'Failed' },
          ].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)} style={{
              padding: '6px 14px', borderRadius: 6, border: '1px solid',
              borderColor: filter === f.key ? '#2563EB' : '#E5E7EB',
              background: filter === f.key ? 'rgba(37,99,235,0.08)' : '#FFFFFF',
              color: filter === f.key ? '#2563EB' : '#6B7280',
              fontSize: 13, fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
            }}>
              {f.label}
            </button>
          ))}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{
              padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
              background: '#FFFFFF', color: '#374151', fontSize: 13, outline: 'none',
            }}
          >
            <option value="scenario">{isEs ? 'Nombre' : 'Name'}</option>
            <option value="latency">{isEs ? 'Latencia' : 'Latency'}</option>
            <option value="quality">{isEs ? 'Calidad' : 'Quality'}</option>
          </select>
        </div>
      </div>

      {/* Results table */}
      <div style={{
        background: '#FFFFFF', borderRadius: 14, border: '1px solid #E5E7EB',
        overflow: 'hidden', marginBottom: 24,
      }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#F9FAFB' }}>
                {[
                  isEs ? 'Escenario' : 'Scenario',
                  'Suite',
                  isEs ? 'Estado' : 'Status',
                  isEs ? 'Latencia' : 'Latency',
                  isEs ? 'Calidad' : 'Quality',
                  'Tokens',
                  'Fallback',
                ].map((h, i) => (
                  <th key={i} style={{
                    textAlign: 'left', padding: '10px 14px', color: '#6B7280',
                    fontWeight: 600, fontSize: 11, textTransform: 'uppercase',
                    borderBottom: '1px solid #E5E7EB',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredDetails.map((d, i) => (
                <tr key={i} style={{
                  borderBottom: '1px solid #F3F4F6',
                  transition: 'background 0.1s',
                }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#F9FAFB'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#111827', fontWeight: 500 }}>
                    {d.scenario}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 6,
                      background: d.suite === 'Enterprise Ops' ? 'rgba(37,99,235,0.1)' : d.suite === 'Document Intel' ? 'rgba(16,185,129,0.1)' : 'rgba(139,92,246,0.1)',
                      color: d.suite === 'Enterprise Ops' ? '#2563EB' : d.suite === 'Document Intel' ? '#10B981' : '#8B5CF6',
                    }}>
                      {d.suite}
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      fontSize: 11, padding: '3px 10px', borderRadius: 6, fontWeight: 600,
                      background: d.status === 'passed' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                      color: d.status === 'passed' ? '#10B981' : '#EF4444',
                    }}>
                      {d.status === 'passed' ? '\u2713' : '\u2717'} {d.status === 'passed' ? (isEs ? 'Aprobado' : 'Passed') : (isEs ? 'Fallido' : 'Failed')}
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: d.latency > 200 ? '#F59E0B' : '#374151' }}>
                    {d.latency}ms
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{
                        width: 48, height: 4, borderRadius: 2, background: '#E5E7EB', overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%', width: `${d.quality * 100}%`, borderRadius: 2,
                          background: d.quality >= 0.9 ? '#10B981' : d.quality >= 0.7 ? '#F59E0B' : '#EF4444',
                        }} />
                      </div>
                      <span style={{
                        fontFamily: 'monospace', fontSize: 12,
                        color: d.quality >= 0.9 ? '#10B981' : d.quality >= 0.7 ? '#F59E0B' : '#EF4444',
                        fontWeight: 600,
                      }}>{d.quality.toFixed(2)}</span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#9CA3AF', fontSize: 12 }}>
                    {d.tokens.toLocaleString()}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {d.fallback ? (
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: 'rgba(245,158,11,0.12)', color: '#F59E0B', fontWeight: 600 }}>
                        {isEs ? 'Si' : 'Yes'}
                      </span>
                    ) : (
                      <span style={{ fontSize: 11, color: '#D1D5DB' }}>--</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Run History / Comparison */}
      <div style={{
        background: '#FFFFFF', borderRadius: 14, padding: 20,
        border: '1px solid #E5E7EB',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 14 }}>
          {isEs ? 'Historial de Ejecuciones' : 'Run History'}
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                {[
                  '#',
                  isEs ? 'Fecha' : 'Timestamp',
                  isEs ? 'Tasa Aprobacion' : 'Pass Rate',
                  isEs ? 'Latencia Prom.' : 'Avg Latency',
                  isEs ? 'Calidad Prom.' : 'Avg Quality',
                  isEs ? 'Tendencia' : 'Trend',
                ].map((h, i) => (
                  <th key={i} style={{
                    textAlign: 'left', padding: '8px 12px', color: '#6B7280',
                    fontWeight: 600, fontSize: 11, textTransform: 'uppercase',
                    borderBottom: '1px solid #E5E7EB',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runHistory.map((run, i) => {
                const prev = runHistory[i + 1]
                const trend = prev ? (run.pass_rate >= prev.pass_rate ? 'up' : 'down') : 'neutral'
                return (
                  <tr key={run.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={{ padding: '8px 12px', color: '#9CA3AF' }}>{run.id}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#374151' }}>{run.timestamp}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        fontWeight: 600,
                        color: run.pass_rate >= 0.85 ? '#10B981' : run.pass_rate >= 0.7 ? '#F59E0B' : '#EF4444',
                      }}>
                        {(run.pass_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#374151' }}>{run.avg_latency}ms</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#374151' }}>{run.avg_quality.toFixed(2)}</td>
                    <td style={{ padding: '8px 12px' }}>
                      {trend === 'up' && <span style={{ color: '#10B981', fontWeight: 600 }}>{'\u25B2'} {isEs ? 'Mejora' : 'Improved'}</span>}
                      {trend === 'down' && <span style={{ color: '#EF4444', fontWeight: 600 }}>{'\u25BC'} {isEs ? 'Baja' : 'Regressed'}</span>}
                      {trend === 'neutral' && <span style={{ color: '#9CA3AF' }}>--</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* CSS for spinner */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
