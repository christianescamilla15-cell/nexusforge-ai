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
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB',
      padding: 24, animation: 'fadeIn 0.2s ease-out',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#111827', margin: 0 }}>{agent.name}</h2>
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
            background: '#F3F4F6', border: 'none', borderRadius: 8,
            width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#9CA3AF',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>

      {/* Description */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 6 }}>Descripción</div>
        <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.6, margin: 0 }}>{agent.description}</p>
      </div>

      {/* Tools */}
      {agent.tools && agent.tools.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>Herramientas</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {agent.tools.map((tool) => (
              <span key={tool} style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                background: 'rgba(99,102,241,0.1)', color: '#6366F1', fontWeight: 500,
              }}>{tool}</span>
            ))}
          </div>
        </div>
      )}

      {/* System prompt */}
      {agent.system_prompt && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>Prompt del Sistema</div>
          <pre style={{
            background: '#F9FAFB', borderRadius: 8, padding: 14, fontSize: 12,
            color: '#374151', overflow: 'auto', maxHeight: 200, margin: 0,
            border: '1px solid #E5E7EB', whiteSpace: 'pre-wrap',
          }}>
            {agent.system_prompt}
          </pre>
        </div>
      )}

      {/* Configuration */}
      {agent.config && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 8 }}>Configuración</div>
          <pre style={{
            background: '#F9FAFB', borderRadius: 8, padding: 14, fontSize: 12,
            color: '#4B5563', overflow: 'auto', maxHeight: 200, margin: 0,
            border: '1px solid #E5E7EB',
          }}>
            {JSON.stringify(agent.config, null, 2)}
          </pre>
        </div>
      )}

      {/* Execution stats */}
      {agent.stats && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 10 }}>Estadísticas</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              { label: 'Ejecuciones', value: agent.stats.total_runs?.toLocaleString() || '0' },
              { label: 'Duración Prom.', value: agent.stats.avg_duration ? `${(agent.stats.avg_duration / 1000).toFixed(1)}s` : '--' },
              { label: 'Éxito', value: agent.stats.success_rate != null ? `${(agent.stats.success_rate * 100).toFixed(0)}%` : '--', color: '#10B981' },
            ].map((s) => (
              <div key={s.label} style={{
                background: '#F9FAFB', borderRadius: 8, padding: 12, textAlign: 'center',
                border: '1px solid #E5E7EB',
              }}>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: s.color || '#111827' }}>{s.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent customization notice */}
      <div style={{
        background: '#FFFBEB', borderRadius: 8, padding: 14,
        border: '1px solid #FDE68A', display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round">
          <path d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <span style={{ fontSize: 13, color: '#92400E' }}>
          Agent configuration coming soon / Configuración de agentes próximamente
        </span>
      </div>
    </div>
  )
}
