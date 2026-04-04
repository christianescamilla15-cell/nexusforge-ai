export default function AgentActivity({ agents }) {
  const max = Math.max(...agents.map((a) => a.count || 0), 1)

  return (
    <div style={{
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB', padding: 20,
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 20 }}>
        Actividad de Agentes
      </h3>
      {agents.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#9CA3AF', fontSize: 14, padding: 20 }}>
          Sin datos de agentes
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {agents.map((agent) => (
            <div key={agent.name}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', marginBottom: 6,
                fontSize: 13,
              }}>
                <span style={{ color: '#111827', fontWeight: 500 }}>{agent.name}</span>
                <span style={{ color: '#9CA3AF' }}>{agent.count} ejecuciones</span>
              </div>
              <div style={{
                height: 8, borderRadius: 4,
                background: '#F3F4F6', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', borderRadius: 4,
                  width: `${(agent.count / max) * 100}%`,
                  background: `linear-gradient(90deg, ${agent.color || '#2563EB'}, ${agent.colorEnd || '#60A5FA'})`,
                  transition: 'width 0.6s ease-out',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
