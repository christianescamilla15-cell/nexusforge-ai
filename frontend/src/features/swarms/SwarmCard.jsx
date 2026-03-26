const TOPOLOGY_DATA = {
  sequential: {
    color: '#6366F1',
    bg: 'rgba(99,102,241,0.12)',
    glow: 'rgba(99,102,241,0.25)',
    description: 'Los agentes ejecutan en cadena, cada uno pasa su resultado al siguiente. Ideal para pipelines de procesamiento lineal.',
    diagram: (color) => (
      <svg width="180" height="50" viewBox="0 0 180 50" fill="none" aria-hidden="true">
        {[0, 1, 2, 3].map((i) => (
          <g key={i}>
            <circle cx={20 + i * 45} cy={25} r={10} stroke={color} strokeWidth="1.5" fill="none" />
            <text x={20 + i * 45} y={29} textAnchor="middle" fill={color} fontSize="10" fontWeight="600">{i + 1}</text>
            {i < 3 && (
              <line x1={32 + i * 45} y1={25} x2={53 + i * 45} y2={25} stroke={color} strokeWidth="1.5" markerEnd="url(#arrowSeq)" />
            )}
          </g>
        ))}
        <defs>
          <marker id="arrowSeq" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0 0L6 3L0 6" fill={color} />
          </marker>
        </defs>
      </svg>
    ),
  },
  parallel: {
    color: '#10B981',
    bg: 'rgba(16,185,129,0.12)',
    glow: 'rgba(16,185,129,0.25)',
    description: 'Todos los agentes ejecutan simultaneamente y sus resultados se combinan al final. Maximo rendimiento.',
    diagram: (color) => (
      <svg width="180" height="60" viewBox="0 0 180 60" fill="none" aria-hidden="true">
        <circle cx={20} cy={30} r={10} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={20} y={34} textAnchor="middle" fill={color} fontSize="10" fontWeight="600">S</text>
        {[10, 30, 50].map((y, i) => (
          <g key={i}>
            <line x1={32} y1={30} x2={75} y2={y} stroke={color} strokeWidth="1" />
            <circle cx={85} cy={y} r={8} stroke={color} strokeWidth="1.5" fill="none" />
            <text x={85} y={y + 4} textAnchor="middle" fill={color} fontSize="8" fontWeight="600">{i + 1}</text>
            <line x1={95} y1={y} x2={140} y2={30} stroke={color} strokeWidth="1" />
          </g>
        ))}
        <circle cx={150} cy={30} r={10} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={150} y={34} textAnchor="middle" fill={color} fontSize="10" fontWeight="600">E</text>
      </svg>
    ),
  },
  hierarchical: {
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.12)',
    glow: 'rgba(245,158,11,0.25)',
    description: 'Un agente lider coordina sub-agentes en estructura de arbol. Perfecto para tareas complejas con subtareas.',
    diagram: (color) => (
      <svg width="180" height="70" viewBox="0 0 180 70" fill="none" aria-hidden="true">
        <circle cx={90} cy={12} r={10} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={90} y={16} textAnchor="middle" fill={color} fontSize="9" fontWeight="600">L</text>
        {[45, 135].map((x, i) => (
          <g key={i}>
            <line x1={90} y1={23} x2={x} y2={37} stroke={color} strokeWidth="1" />
            <circle cx={x} cy={42} r={8} stroke={color} strokeWidth="1.5" fill="none" />
            <text x={x} y={46} textAnchor="middle" fill={color} fontSize="8" fontWeight="600">{i + 1}</text>
          </g>
        ))}
        {[20, 70, 110, 160].map((x, i) => (
          <g key={i}>
            <line x1={i < 2 ? 45 : 135} y1={50} x2={x} y2={58} stroke={color} strokeWidth="1" />
            <circle cx={x} cy={63} r={6} stroke={color} strokeWidth="1" fill="none" />
          </g>
        ))}
      </svg>
    ),
  },
  debate: {
    color: '#EC4899',
    bg: 'rgba(236,72,153,0.12)',
    glow: 'rgba(236,72,153,0.25)',
    description: 'Agentes debaten entre si con argumentos y contra-argumentos. Un juez selecciona la mejor respuesta.',
    diagram: (color) => (
      <svg width="180" height="60" viewBox="0 0 180 60" fill="none" aria-hidden="true">
        <circle cx={45} cy={30} r={12} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={45} y={34} textAnchor="middle" fill={color} fontSize="9" fontWeight="600">A</text>
        <circle cx={135} cy={30} r={12} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={135} y={34} textAnchor="middle" fill={color} fontSize="9" fontWeight="600">B</text>
        <path d="M59 24 L121 24" stroke={color} strokeWidth="1" markerEnd="url(#arrowDeb)" />
        <path d="M121 36 L59 36" stroke={color} strokeWidth="1" markerEnd="url(#arrowDeb)" />
        <circle cx={90} cy={55} r={8} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={90} y={58} textAnchor="middle" fill={color} fontSize="7" fontWeight="600">J</text>
        <line x1={52} y1={42} x2={83} y2={50} stroke={color} strokeWidth="1" strokeDasharray="3" />
        <line x1={128} y1={42} x2={97} y2={50} stroke={color} strokeWidth="1" strokeDasharray="3" />
        <defs>
          <marker id="arrowDeb" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0 0L6 3L0 6" fill={color} />
          </marker>
        </defs>
      </svg>
    ),
  },
  consensus: {
    color: '#8B5CF6',
    bg: 'rgba(139,92,246,0.12)',
    glow: 'rgba(139,92,246,0.25)',
    description: 'Multiples agentes votan sobre la respuesta correcta. Se requiere mayoria para alcanzar consenso.',
    diagram: (color) => (
      <svg width="180" height="60" viewBox="0 0 180 60" fill="none" aria-hidden="true">
        {[30, 90, 150].map((x, i) => (
          <g key={i}>
            <circle cx={x} cy={15} r={9} stroke={color} strokeWidth="1.5" fill="none" />
            <text x={x} y={19} textAnchor="middle" fill={color} fontSize="8" fontWeight="600">{i + 1}</text>
            <line x1={x} y1={25} x2={90} y2={45} stroke={color} strokeWidth="1" />
          </g>
        ))}
        <circle cx={90} cy={50} r={8} stroke={color} strokeWidth="1.5" fill={color} fillOpacity="0.2" />
        <text x={90} y={53} textAnchor="middle" fill={color} fontSize="7" fontWeight="700">OK</text>
      </svg>
    ),
  },
  adaptive: {
    color: '#60A5FA',
    bg: 'rgba(96,165,250,0.12)',
    glow: 'rgba(96,165,250,0.25)',
    description: 'La topologia cambia dinamicamente segun los resultados. Se adapta al contexto en tiempo real.',
    diagram: (color) => (
      <svg width="180" height="60" viewBox="0 0 180 60" fill="none" aria-hidden="true">
        <circle cx={25} cy={30} r={10} stroke={color} strokeWidth="1.5" fill="none" />
        <text x={25} y={34} textAnchor="middle" fill={color} fontSize="12" fontWeight="600">?</text>
        <line x1={37} y1={30} x2={65} y2={15} stroke={color} strokeWidth="1" strokeDasharray="4" />
        <line x1={37} y1={30} x2={65} y2={30} stroke={color} strokeWidth="1" strokeDasharray="4" />
        <line x1={37} y1={30} x2={65} y2={45} stroke={color} strokeWidth="1" strokeDasharray="4" />
        {[15, 30, 45].map((y, i) => (
          <g key={i}>
            <rect x={68} y={y - 7} width={40} height={14} rx={4} stroke={color} strokeWidth="1" fill="none" />
            <text x={88} y={y + 3} textAnchor="middle" fill={color} fontSize="7">{['Seq', 'Par', 'Deb'][i]}</text>
            <line x1={110} y1={y} x2={140} y2={30} stroke={color} strokeWidth="1" strokeDasharray="4" />
          </g>
        ))}
        <circle cx={155} cy={30} r={10} stroke={color} strokeWidth="1.5" fill={color} fillOpacity="0.15" />
        <text x={155} y={33} textAnchor="middle" fill={color} fontSize="8" fontWeight="600">R</text>
      </svg>
    ),
  },
}

export default function SwarmCard({ topology, onExecute }) {
  const data = TOPOLOGY_DATA[topology]
  if (!data) return null

  const name = topology.charAt(0).toUpperCase() + topology.slice(1)

  return (
    <div
      aria-label={`Topologia ${name}`}
      style={{
        background: '#161E2E',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 12,
        padding: 20,
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = `0 0 20px ${data.glow}`
        e.currentTarget.style.borderColor = `${data.color}44`
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8, background: data.bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 700, color: data.color,
        }}>
          {name[0]}
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>{name}</div>
          <span style={{
            fontSize: 11, padding: '1px 7px', borderRadius: 6,
            background: data.bg, color: data.color, fontWeight: 500,
          }}>topology</span>
        </div>
      </div>

      {/* Description */}
      <p style={{ fontSize: 13, color: '#9CA3AF', lineHeight: 1.5, margin: '0 0 14px' }}>
        {data.description}
      </p>

      {/* Diagram */}
      <div style={{
        background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: '12px 8px',
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14,
        minHeight: 70,
      }}>
        {data.diagram(data.color)}
      </div>

      {/* Execute button */}
      <button
        onClick={() => onExecute && onExecute(topology)}
        aria-label={`Ejecutar topologia ${name}`}
        style={{
          width: '100%', padding: '9px 0', borderRadius: 8, border: 'none',
          background: data.bg, color: data.color, fontSize: 13, fontWeight: 600,
          cursor: 'pointer', transition: 'all 0.15s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = data.color
          e.currentTarget.style.color = '#0A0B0F'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = data.bg
          e.currentTarget.style.color = data.color
        }}
      >
        Ejecutar
      </button>
    </div>
  )
}

export { TOPOLOGY_DATA }
