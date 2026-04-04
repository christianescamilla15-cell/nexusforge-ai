import { useState } from 'react'
import StatusBadge from '../../shared/components/StatusBadge'

const DOT_COLORS = {
  pending: '#9CA3AF',
  running: '#6366F1',
  completed: '#10B981',
  failed: '#EF4444',
}

function formatMs(ms) {
  if (!ms && ms !== 0) return '--'
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

function JsonBlock({ data, label }) {
  if (!data) return null
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase' }}>{label}</div>
      <pre style={{
        background: '#F9FAFB', borderRadius: 8, padding: 12, fontSize: 12,
        color: '#4B5563', overflow: 'auto', maxHeight: 200, margin: 0,
        border: '1px solid #E5E7EB',
      }}>
        {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

function MetricPill({ label, value, color, mono }) {
  return (
    <div style={{
      display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
      padding: '6px 12px', borderRadius: 8, background: '#F9FAFB',
      border: '1px solid #E5E7EB', minWidth: 70,
    }}>
      <span style={{ fontSize: 10, color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: color || '#111827', fontFamily: mono ? 'monospace' : 'inherit' }}>{value}</span>
    </div>
  )
}

export default function StepTimeline({ steps }) {
  const [expanded, setExpanded] = useState({})

  const toggle = (idx) => setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }))

  return (
    <div style={{ position: 'relative', paddingLeft: 28 }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute', left: 9, top: 12, bottom: 12, width: 2,
        background: '#E5E7EB',
      }} />

      {steps.map((step, idx) => {
        const dotColor = DOT_COLORS[step.status] || DOT_COLORS.pending
        const isRunning = step.status === 'running'
        const isFailed = step.status === 'failed'
        const isExpanded = expanded[idx]

        return (
          <div key={idx} style={{ position: 'relative', marginBottom: 16 }}>
            {/* Dot */}
            <div style={{
              position: 'absolute', left: -28 + 4, top: 16, width: 12, height: 12,
              borderRadius: '50%', background: dotColor, zIndex: 2,
              boxShadow: isRunning ? `0 0 8px ${dotColor}` : 'none',
              animation: isRunning ? 'pulse 1.5s infinite' : 'none',
            }} />

            {/* Card */}
            <div
              onClick={() => toggle(idx)}
              role="button"
              tabIndex={0}
              aria-label={`Step ${step.name || idx + 1}: ${step.status}`}
              onKeyDown={(e) => e.key === 'Enter' && toggle(idx)}
              style={{
                background: '#FFFFFF', borderRadius: 10,
                border: `1px solid ${isFailed ? 'rgba(239,68,68,0.3)' : isExpanded ? 'rgba(99,102,241,0.3)' : '#E5E7EB'}`,
                padding: '14px 18px', cursor: 'pointer', transition: 'all 0.2s',
                boxShadow: isExpanded ? '0 2px 12px rgba(99,102,241,0.08)' : 'none',
              }}
              onMouseEnter={(e) => { if (!isExpanded) e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)' }}
              onMouseLeave={(e) => { if (!isExpanded) e.currentTarget.style.borderColor = isFailed ? 'rgba(239,68,68,0.3)' : '#E5E7EB' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{step.name || `Step ${idx + 1}`}</span>
                  {step.agent_type && (
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 6,
                      background: 'rgba(99,102,241,0.12)', color: '#6366F1',
                    }}>{step.agent_type}</span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <StatusBadge status={step.status} />
                  <span style={{ fontSize: 12, color: '#9CA3AF' }}>{formatMs(step.duration_ms)}</span>
                  {step.tokens != null && (
                    <span style={{ fontSize: 12, color: '#9CA3AF' }}>{Number(step.tokens ?? 0).toLocaleString()} tok</span>
                  )}
                  {step.cost != null && (
                    <span style={{ fontSize: 12, color: '#10B981' }}>${Number(step.cost ?? 0).toFixed(4)}</span>
                  )}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"
                    style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
              </div>

              {isFailed && step.error && (
                <div style={{
                  marginTop: 10, padding: '8px 12px', borderRadius: 6,
                  background: 'rgba(239,68,68,0.1)', color: '#DC2626', fontSize: 13,
                }}>
                  {step.error}
                </div>
              )}

              {/* Expanded: Step Inspector (LangSmith-style) */}
              {isExpanded && (
                <div style={{ marginTop: 14, borderTop: '1px solid #E5E7EB', paddingTop: 14 }} onClick={(e) => e.stopPropagation()}>
                  {/* Metrics row */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
                    {step.agent_type && (
                      <MetricPill label="Agent" value={step.agent_type} color="#6366F1" />
                    )}
                    {step.model && (
                      <MetricPill label="Model" value={step.model} color="#2563EB" mono />
                    )}
                    {step.provider && (
                      <MetricPill label="Provider" value={step.provider} color="#8B5CF6" />
                    )}
                    {step.duration_ms != null && (
                      <MetricPill label="Latency" value={`${step.duration_ms}ms`} color="#F59E0B" mono />
                    )}
                    {step.tokens_in != null && (
                      <MetricPill label="Tokens In" value={step.tokens_in.toLocaleString()} mono />
                    )}
                    {step.tokens_out != null && (
                      <MetricPill label="Tokens Out" value={step.tokens_out.toLocaleString()} mono />
                    )}
                    {step.tokens != null && (
                      <MetricPill label="Total Tokens" value={step.tokens.toLocaleString()} mono />
                    )}
                    {step.cost != null && (
                      <MetricPill label="Cost" value={`$${Number(step.cost ?? 0).toFixed(4)}`} color="#10B981" mono />
                    )}
                    {step.retries != null && step.retries > 0 && (
                      <MetricPill label="Retries" value={step.retries} color="#EF4444" />
                    )}
                    {step.fallback_used && (
                      <MetricPill label="Fallback" value={step.fallback_provider || 'Yes'} color="#EC4899" />
                    )}
                  </div>

                  {/* Retry / Fallback info bar */}
                  {(step.retries > 0 || step.fallback_used) && (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                      borderRadius: 8, background: 'rgba(245,158,11,0.08)',
                      border: '1px solid rgba(245,158,11,0.2)', marginBottom: 12, fontSize: 12,
                    }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                      <span style={{ color: '#92400E' }}>
                        {step.retries > 0 && `${step.retries} retries performed. `}
                        {step.fallback_used && `Fallback to ${step.fallback_provider || 'alternate provider'}.`}
                      </span>
                    </div>
                  )}

                  {/* Input / Output JSON */}
                  <div style={{ display: 'grid', gridTemplateColumns: step.input && step.output ? '1fr 1fr' : '1fr', gap: 12 }}>
                    {step.input && <JsonBlock data={step.input} label="Input" />}
                    {step.output && <JsonBlock data={step.output} label="Output" />}
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
