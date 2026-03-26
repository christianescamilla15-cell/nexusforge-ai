export default function AgentActivity({ agents }) {
  const max = Math.max(...agents.map((a) => a.count), 1)

  return (
    <div style={{
      background: '#161E2E', borderRadius: 12,
      border: '1px solid rgba(255,255,255,0.06)', padding: 20,
    }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB', marginBottom: 20 }}>
        Actividad de Agentes
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {agents.map((agent) => (
          <div key={agent.name}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', marginBottom: 6,
              fontSize: 13,
            }}>
              <span style={{ color: '#E5E7EB' }}>{agent.name}</span>
              <span style={{ color: '#9CA3AF' }}>{agent.count} ejecuciones</span>
            </div>
            <div style={{
              height: 8, borderRadius: 4,
              background: 'rgba(255,255,255,0.04)', overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: 4,
                width: `${(agent.count / max) * 100}%`,
                background: `linear-gradient(90deg, ${agent.color || '#6366F1'}, ${agent.colorEnd || '#8B5CF6'})`,
                transition: 'width 0.6s ease-out',
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
