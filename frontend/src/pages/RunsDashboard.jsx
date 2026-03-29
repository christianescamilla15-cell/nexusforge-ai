import { useState, useEffect } from 'react'

const API = '/api/runs'

export default function RunsDashboard() {
  const [runs, setRuns] = useState([])
  const [health, setHealth] = useState(null)
  const [selectedRun, setSelectedRun] = useState(null)
  const [timeline, setTimeline] = useState([])

  useEffect(() => {
    fetch(API).then(r => r.json()).then(d => setRuns(d.runs || []))
    fetch('/api/runs/reliability/health').then(r => r.json()).then(setHealth)
  }, [])

  const selectRun = async (runId) => {
    setSelectedRun(runId)
    const res = await fetch(`${API}/${runId}/timeline`)
    const data = await res.json()
    setTimeline(data.timeline || [])
  }

  const statusColor = (status) => ({
    completed: '#059669', failed: '#DC2626', running: '#2563EB', pending: '#9CA3AF',
  }[status] || '#9CA3AF')

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 24px', fontFamily: "'Inter', -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        NexusForge Observability
      </h1>
      <p style={{ color: '#4B5563', marginBottom: 32 }}>
        Workflow execution history, agent timeline, and reliability metrics
      </p>

      {/* System Health */}
      {health && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
          {[
            { label: 'Total Runs', value: health.total_runs },
            { label: 'Success Rate', value: `${(health.system_success_rate * 100).toFixed(1)}%` },
            { label: 'Agents Tracked', value: health.total_agents_tracked },
            { label: 'Failed Runs', value: health.failed_runs },
          ].map((m, i) => (
            <div key={i} style={{
              background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 12, padding: 20,
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>{m.value}</div>
              <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{m.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selectedRun ? '1fr 1fr' : '1fr', gap: 24 }}>
        {/* Runs Table */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Recent Runs</h2>
          <div style={{ border: '1px solid #E5E7EB', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
            {runs.map((run, i) => (
              <div key={run.id} onClick={() => selectRun(run.id)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '14px 20px', cursor: 'pointer',
                  borderBottom: i < runs.length - 1 ? '1px solid #F3F4F6' : 'none',
                  background: selectedRun === run.id ? '#F9FAFB' : '#FFFFFF',
                  transition: 'background 0.15s',
                }}
              >
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{run.workflow_name}</div>
                  <div style={{ fontSize: 12, color: '#9CA3AF' }}>{run.id.slice(0, 8)}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 12, color: '#4B5563' }}>{run.total_latency_ms ? `${run.total_latency_ms}ms` : '--'}</span>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 100,
                    background: statusColor(run.status) + '12', color: statusColor(run.status),
                  }}>{run.status}</span>
                </div>
              </div>
            ))}
            {runs.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF' }}>No runs recorded yet</div>
            )}
          </div>
        </div>

        {/* Timeline */}
        {selectedRun && (
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Timeline</h2>
            <div style={{ border: '1px solid #E5E7EB', borderRadius: 12, padding: 20, background: '#FFFFFF', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              {timeline.map((e, i) => (
                <div key={i} style={{
                  display: 'flex', gap: 12, padding: '10px 0',
                  borderBottom: i < timeline.length - 1 ? '1px solid #F3F4F6' : 'none',
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', marginTop: 6, flexShrink: 0,
                    background: e.event.includes('fail') ? '#DC2626'
                      : e.event.includes('fallback') ? '#D97706'
                      : e.event.includes('retry') ? '#D97706'
                      : e.event.includes('completed') ? '#059669'
                      : '#2563EB',
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{e.event}</div>
                    {e.agent && <div style={{ fontSize: 12, color: '#4B5563' }}>agent: {e.agent}</div>}
                    {e.payload?.latency_ms && <div style={{ fontSize: 12, color: '#9CA3AF' }}>{e.payload.latency_ms}ms</div>}
                  </div>
                  <div style={{ fontSize: 11, color: '#9CA3AF', whiteSpace: 'nowrap' }}>
                    {new Date(e.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
              {timeline.length === 0 && (
                <div style={{ textAlign: 'center', color: '#9CA3AF', padding: 20 }}>No events</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Agent Reliability */}
      {health?.agents?.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Agent Reliability</h2>
          <div style={{ border: '1px solid #E5E7EB', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', padding: '12px 20px', background: '#F9FAFB', fontSize: 11, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              <span>Agent</span><span>Executions</span><span>Success Rate</span><span>Avg Latency</span><span>Fallbacks</span>
            </div>
            {health.agents.map((a, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', padding: '14px 20px', borderTop: '1px solid #F3F4F6', fontSize: 14, color: '#374151' }}>
                <span style={{ fontWeight: 600 }}>{a.agent}</span>
                <span>{a.executions}</span>
                <span style={{ color: a.success_rate >= 0.9 ? '#059669' : a.success_rate >= 0.7 ? '#D97706' : '#DC2626' }}>
                  {(a.success_rate * 100).toFixed(0)}%
                </span>
                <span>{a.avg_latency_ms}ms</span>
                <span>{a.fallbacks}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
