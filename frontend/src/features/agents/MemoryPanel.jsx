const TIERS = [
  {
    name: 'Working Memory',
    storage: 'In-Memory (Dict)',
    ttl: '5 min',
    color: '#60A5FA',
    bg: 'rgba(96,165,250,0.12)',
    border: 'rgba(96,165,250,0.2)',
    icon: 'M12 6v6l4 2',
    examples: [
      { key: 'current_task', value: '"Clasificar doc_47.pdf"' },
      { key: 'step_index', value: '3' },
      { key: 'temp_context', value: '{ tokens: 1247 }' },
    ],
    desc: 'Datos temporales de la ejecucion actual. Se elimina al completar la tarea.',
  },
  {
    name: 'Episodic Memory',
    storage: 'SQLite / Redis',
    ttl: '24 horas',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.12)',
    border: 'rgba(245,158,11,0.2)',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    examples: [
      { key: 'last_error', value: '"timeout en paso 2"' },
      { key: 'run_2024_q4', value: '{ success: true, dur: 4.2s }' },
      { key: 'agent_perf', value: '{ avg: 0.94, runs: 127 }' },
    ],
    desc: 'Historial de ejecuciones recientes. Permite aprender de errores anteriores.',
  },
  {
    name: 'Semantic Memory',
    storage: 'Vector DB (Chroma)',
    ttl: 'Permanente',
    color: '#10B981',
    bg: 'rgba(16,185,129,0.12)',
    border: 'rgba(16,185,129,0.2)',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
    examples: [
      { key: 'doc_patterns', value: '[ embedding_512d ]' },
      { key: 'entity_graph', value: '{ nodes: 342, edges: 891 }' },
      { key: 'domain_rules', value: '{ rules: 28, version: 3 }' },
    ],
    desc: 'Conocimiento permanente con embeddings. Busqueda semantica por similaridad.',
  },
]

export default function MemoryPanel() {
  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          Sistema de Memoria 3-Tier
        </h2>
        <p style={{ fontSize: 13, color: '#9CA3AF' }}>
          Los datos fluyen de Working a Episodic al completar tareas, y a Semantic cuando se detectan patrones persistentes.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {TIERS.map((tier, idx) => (
          <div key={tier.name}>
            <div
              aria-label={`Tier de memoria: ${tier.name}`}
              style={{
                background: '#FFFFFF',
                border: `1px solid ${tier.border}`,
                borderRadius: 12,
                padding: 20,
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = `0 0 16px ${tier.border}`
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              {/* Tier header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, background: tier.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                    stroke={tier.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d={tier.icon} />
                  </svg>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: tier.color }}>{tier.name}</div>
                  <div style={{ fontSize: 12, color: '#9CA3AF' }}>{tier.desc}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: '#9CA3AF' }}>Almacenamiento</div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: '#111827' }}>{tier.storage}</div>
                </div>
                <div style={{ textAlign: 'right', marginLeft: 12 }}>
                  <div style={{ fontSize: 11, color: '#9CA3AF' }}>TTL</div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: tier.color }}>{tier.ttl}</div>
                </div>
              </div>

              {/* Example data */}
              <div style={{
                background: '#F3F4F6', borderRadius: 8, padding: 10,
                fontFamily: 'monospace', fontSize: 12,
              }}>
                {tier.examples.map((ex) => (
                  <div key={ex.key} style={{ display: 'flex', gap: 8, padding: '3px 0' }}>
                    <span style={{ color: tier.color, minWidth: 120 }}>{ex.key}:</span>
                    <span style={{ color: '#9CA3AF' }}>{ex.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Flow arrow between tiers */}
            {idx < TIERS.length - 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 5v14M12 19l-4-4M12 19l4-4" stroke="#4B5563" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
