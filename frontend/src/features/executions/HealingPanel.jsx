const STRATEGIES = [
  {
    name: 'Retry',
    color: '#6366F1',
    bg: 'rgba(99,102,241,0.12)',
    description: 'Reintenta la operacion con backoff exponencial. Efectivo para errores transitorios de red.',
    when: 'network_error, timeout, rate_limit',
    successRate: 94,
    icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  },
  {
    name: 'Skip',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.12)',
    description: 'Omite el paso fallido y continua con el siguiente. Para pasos no criticos del pipeline.',
    when: 'optional_step, non_critical_error',
    successRate: 100,
    icon: 'M13 5l7 7-7 7M5 5l7 7-7 7',
  },
  {
    name: 'Repair',
    color: '#10B981',
    bg: 'rgba(16,185,129,0.12)',
    description: 'Usa un agente reparador para corregir datos malformados antes de reintentar.',
    when: 'data_quality, validation_error, format_mismatch',
    successRate: 87,
    icon: 'M11.42 15.17l-5.66-5.66a8 8 0 1111.31 0l-5.65 5.66zM11.42 15.17L7.75 18.84M11.42 15.17l3.66 3.67',
  },
  {
    name: 'Escalate',
    color: '#EC4899',
    bg: 'rgba(236,72,153,0.12)',
    description: 'Escala a un agente mas capaz (modelo superior) cuando el actual no puede resolver.',
    when: 'complexity_exceeded, confidence_low',
    successRate: 91,
    icon: 'M5 10l7-7m0 0l7 7m-7-7v18',
  },
  {
    name: 'Fallback',
    color: '#8B5CF6',
    bg: 'rgba(139,92,246,0.12)',
    description: 'Activa una ruta alternativa predefinida cuando la principal falla repetidamente.',
    when: 'max_retries_exceeded, critical_failure',
    successRate: 96,
    icon: 'M9 17V7m0 10l-3-3m3 3l3-3M15 7v10m0-10l3 3m-3-3l-3 3',
  },
]

const ERROR_MAP = [
  { error: 'network_error', strategy: 'Retry', color: '#6366F1' },
  { error: 'timeout', strategy: 'Retry', color: '#6366F1' },
  { error: 'rate_limit', strategy: 'Retry', color: '#6366F1' },
  { error: 'data_quality', strategy: 'Repair', color: '#10B981' },
  { error: 'validation_error', strategy: 'Repair', color: '#10B981' },
  { error: 'optional_step', strategy: 'Skip', color: '#F59E0B' },
  { error: 'complexity_exceeded', strategy: 'Escalate', color: '#EC4899' },
  { error: 'critical_failure', strategy: 'Fallback', color: '#8B5CF6' },
]

const HEALING_LOG = [
  { time: '14:32:01', agent: 'EntityExtractor', error: 'timeout', strategy: 'Retry', result: 'Resuelto en intento 2' },
  { time: '14:28:45', agent: 'DataValidator', error: 'data_quality', strategy: 'Repair', result: 'JSON reparado automaticamente' },
  { time: '14:25:12', agent: 'SummaryAgent', error: 'rate_limit', strategy: 'Retry', result: 'Resuelto tras backoff 3s' },
  { time: '14:21:33', agent: 'ContentGen', error: 'complexity_exceeded', strategy: 'Escalate', result: 'Escalado a claude-opus-4' },
  { time: '14:18:07', agent: 'FlowRouter', error: 'optional_step', strategy: 'Skip', result: 'Paso de logging omitido' },
  { time: '14:15:44', agent: 'DocClassifier', error: 'critical_failure', strategy: 'Fallback', result: 'Ruta alternativa activada' },
]

export default function HealingPanel() {
  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>
          Self-Healing Dashboard
        </h2>
        <p style={{ fontSize: 13, color: '#9CA3AF' }}>
          El sistema detecta y resuelve errores automaticamente con 5 estrategias de recuperacion.
        </p>
      </div>

      {/* Strategy cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 12, marginBottom: 24,
      }}>
        {STRATEGIES.map((s) => (
          <div
            key={s.name}
            aria-label={`Estrategia ${s.name}`}
            style={{
              background: '#161E2E', border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 10, padding: 16, transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = `${s.color}44`
              e.currentTarget.style.boxShadow = `0 0 12px ${s.bg}`
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 8, background: s.bg,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                  stroke={s.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d={s.icon} />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB' }}>{s.name}</div>
                <div style={{ fontSize: 11, color: s.color, fontWeight: 500 }}>{s.successRate}% exito</div>
              </div>
            </div>
            <p style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.5, margin: '0 0 8px' }}>
              {s.description}
            </p>
            <div style={{ fontSize: 11, color: '#6B7280' }}>
              Triggers: <span style={{ color: '#9CA3AF' }}>{s.when}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Error classification */}
      <div style={{
        background: '#161E2E', borderRadius: 12, padding: 18,
        border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB', marginBottom: 12 }}>
          Clasificacion de Errores
        </h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {ERROR_MAP.map((e) => (
            <div key={e.error} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'rgba(0,0,0,0.2)', borderRadius: 6, padding: '5px 10px',
            }}>
              <span style={{ fontSize: 12, color: '#9CA3AF', fontFamily: 'monospace' }}>{e.error}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#4B5563" strokeWidth="2" aria-hidden="true">
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
              <span style={{ fontSize: 12, fontWeight: 600, color: e.color }}>{e.strategy}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Healing log */}
      <div style={{
        background: '#161E2E', borderRadius: 12, padding: 18,
        border: '1px solid rgba(255,255,255,0.06)',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB', marginBottom: 12 }}>
          Actividad Reciente de Healing
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {HEALING_LOG.map((log, i) => {
            const strat = STRATEGIES.find((s) => s.name === log.strategy)
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '8px 12px', background: 'rgba(0,0,0,0.2)', borderRadius: 8,
                fontSize: 12,
              }}>
                <span style={{ color: '#6B7280', fontFamily: 'monospace', minWidth: 65 }}>{log.time}</span>
                <span style={{ color: '#E5E7EB', fontWeight: 500, minWidth: 110 }}>{log.agent}</span>
                <span style={{
                  padding: '2px 6px', borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
                  background: 'rgba(255,255,255,0.05)', color: '#9CA3AF', minWidth: 90,
                }}>{log.error}</span>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                  background: strat?.bg || 'transparent', color: strat?.color || '#9CA3AF',
                }}>{log.strategy}</span>
                <span style={{ color: '#10B981', flex: 1 }}>{log.result}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
