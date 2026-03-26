const TYPE_COLORS = {
  classifier: '#818CF8',
  extractor: '#10B981',
  summarizer: '#F59E0B',
  generator: '#A78BFA',
  router: '#EC4899',
  loader: '#60A5FA',
  storage: '#34D399',
  validator: '#FB923C',
}

export default function AgentDetailPanel({ agent, onClose }) {
  if (!agent) return null

  const typeColor = TYPE_COLORS[agent.type] || '#818CF8'

  return (
    <div style={{
      background: '#161E2E', borderRadius: 12,
      border: '1px solid rgba(255,255,255,0.06)',
      padding: 24, animation: 'fadeIn 0.2s ease-out',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#E5E7EB', margin: 0 }}>{agent.name}</h2>
            <span style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: `${typeColor}20`, color: typeColor, fontWeight: 600,
            }}>{agent.type}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: agent.status === 'active' ? '#10B981' : '#F59E0B',
            }} />
            <span style={{ fontSize: 13, color: agent.status === 'active' ? '#10B981' : '#F59E0B' }}>
              {agent.status === 'active' ? 'Activo' : 'Pausado'}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Cerrar panel de detalle"
          style={{
            background: 'rgba(255,255,255,0.04)', border: 'none', borderRadius: 8,
            width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#9CA3AF',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>

      {/* Description */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 6 }}>Descripcion</div>
        <p style={{ fontSize: 14, color: '#D1D5DB', lineHeight: 1.6, margin: 0 }}>{agent.description}</p>
      </div>

      {/* Tools */}
      {agent.tools && agent.tools.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>Herramientas</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {agent.tools.map((tool) => (
              <span key={tool} style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                background: 'rgba(99,102,241,0.1)', color: '#A5B4FC', fontWeight: 500,
              }}>{tool}</span>
            ))}
          </div>
        </div>
      )}

      {/* System prompt */}
      {agent.system_prompt && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>System Prompt</div>
          <pre style={{
            background: '#0A0B0F', borderRadius: 8, padding: 14, fontSize: 12,
            color: '#D1D5DB', overflow: 'auto', maxHeight: 200, margin: 0,
            border: '1px solid rgba(255,255,255,0.06)', whiteSpace: 'pre-wrap',
          }}>
            {agent.system_prompt}
          </pre>
        </div>
      )}

      {/* Configuration */}
      {agent.config && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>Configuracion</div>
          <pre style={{
            background: '#0A0B0F', borderRadius: 8, padding: 14, fontSize: 12,
            color: '#A5B4FC', overflow: 'auto', maxHeight: 200, margin: 0,
            border: '1px solid rgba(255,255,255,0.06)',
          }}>
            {JSON.stringify(agent.config, null, 2)}
          </pre>
        </div>
      )}

      {/* Execution stats */}
      {agent.stats && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 10 }}>Estadisticas</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              { label: 'Ejecuciones', value: agent.stats.total_runs?.toLocaleString() || '0' },
              { label: 'Duracion Prom.', value: agent.stats.avg_duration ? `${(agent.stats.avg_duration / 1000).toFixed(1)}s` : '--' },
              { label: 'Exito', value: agent.stats.success_rate != null ? `${(agent.stats.success_rate * 100).toFixed(0)}%` : '--', color: '#10B981' },
            ].map((s) => (
              <div key={s.label} style={{
                background: '#0A0B0F', borderRadius: 8, padding: 12, textAlign: 'center',
                border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: s.color || '#E5E7EB' }}>{s.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
