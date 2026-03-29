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
              aria-label={`Paso ${step.name || idx + 1}: ${step.status}`}
              onKeyDown={(e) => e.key === 'Enter' && toggle(idx)}
              style={{
                background: '#FFFFFF', borderRadius: 10,
                border: `1px solid ${isFailed ? 'rgba(239,68,68,0.3)' : '#E5E7EB'}`,
                padding: '14px 18px', cursor: 'pointer', transition: 'border-color 0.15s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = isFailed ? 'rgba(239,68,68,0.3)' : '#E5E7EB'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{step.name || `Paso ${idx + 1}`}</span>
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
                    <span style={{ fontSize: 12, color: '#9CA3AF' }}>{step.tokens.toLocaleString()} tok</span>
                  )}
                  {step.cost != null && (
                    <span style={{ fontSize: 12, color: '#10B981' }}>${step.cost.toFixed(4)}</span>
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

              {isExpanded && (
                <div style={{ marginTop: 12, borderTop: '1px solid #E5E7EB', paddingTop: 12 }}>
                  <JsonBlock data={step.input} label="Entrada" />
                  <JsonBlock data={step.output} label="Salida" />
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
