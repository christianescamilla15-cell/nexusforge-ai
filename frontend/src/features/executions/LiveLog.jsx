import { useEffect, useRef, useState } from 'react'

const EVENT_COLORS = {
  step_started: '#6366F1',
  step_completed: '#10B981',
  step_failed: '#EF4444',
  log: '#9CA3AF',
  info: '#60A5FA',
  warning: '#F59E0B',
  error: '#EF4444',
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function LiveLog({ events }) {
  const containerRef = useRef(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [events, autoScroll])

  return (
    <div style={{
      background: '#0A0B0F', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)',
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#E5E7EB' }}>Eventos en Vivo</span>
        <button
          onClick={() => setAutoScroll((a) => !a)}
          aria-label={autoScroll ? 'Pausar auto-scroll' : 'Activar auto-scroll'}
          style={{
            padding: '4px 10px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 500,
            cursor: 'pointer',
            background: autoScroll ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.06)',
            color: autoScroll ? '#818CF8' : '#9CA3AF',
          }}
        >
          {autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
        </button>
      </div>

      <div
        ref={containerRef}
        style={{ maxHeight: 300, overflowY: 'auto', padding: '8px 0', fontFamily: 'monospace' }}
      >
        {events.length === 0 && (
          <div style={{ padding: '20px 16px', color: '#9CA3AF', fontSize: 13, textAlign: 'center' }}>
            Esperando eventos...
          </div>
        )}
        {events.map((evt, idx) => {
          const color = EVENT_COLORS[evt.event_type] || EVENT_COLORS.log
          return (
            <div key={idx} style={{
              display: 'flex', gap: 10, padding: '4px 16px', fontSize: 12,
              lineHeight: '20px',
            }}>
              <span style={{ color: '#6B7280', flexShrink: 0 }}>{formatTime(evt.timestamp)}</span>
              <span style={{
                color, flexShrink: 0, fontWeight: 600, minWidth: 110,
                textTransform: 'uppercase', fontSize: 11,
              }}>
                {evt.event_type}
              </span>
              {evt.step_name && (
                <span style={{ color: '#A5B4FC', flexShrink: 0 }}>[{evt.step_name}]</span>
              )}
              <span style={{ color: '#D1D5DB' }}>{evt.detail || evt.message || ''}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
