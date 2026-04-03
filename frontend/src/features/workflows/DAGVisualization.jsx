import { useMemo } from 'react'

const AGENT_COLORS = {
  orchestrator: '#6366F1',
  classifier: '#10B981',
  summarizer: '#F59E0B',
  extractor: '#06B6D4',
  validator: '#EF4444',
  normalizer: '#8B5CF6',
  enricher: '#EC4899',
  translator: '#14B8A6',
  knowledge: '#3B82F6',
  critic: '#F97316',
  sentiment: '#A855F7',
  default: '#9CA3AF',
}

function getAgentColor(type) {
  return AGENT_COLORS[type] || AGENT_COLORS.default
}

function layoutDAG(steps) {
  if (!steps || !steps.length) return { layers: [], positions: {} }

  const nameToStep = {}
  steps.forEach((s) => { nameToStep[s.name] = s })

  const depths = {}
  function getDepth(name) {
    if (depths[name] !== undefined) return depths[name]
    const step = nameToStep[name]
    if (!step || !step.depends_on || step.depends_on.length === 0) {
      depths[name] = 0
      return 0
    }
    const d = 1 + Math.max(...step.depends_on.map(getDepth))
    depths[name] = d
    return d
  }
  steps.forEach((s) => getDepth(s.name))

  const maxDepth = Math.max(...Object.values(depths), 0)
  const layers = []
  for (let i = 0; i <= maxDepth; i++) {
    layers.push(steps.filter((s) => depths[s.name] === i))
  }

  const nodeW = 180
  const nodeH = 72
  const gapX = 60
  const gapY = 28
  const positions = {}

  layers.forEach((layer, col) => {
    const totalH = layer.length * nodeH + (layer.length - 1) * gapY
    const startY = -totalH / 2
    layer.forEach((step, row) => {
      positions[step.name] = {
        x: col * (nodeW + gapX),
        y: startY + row * (nodeH + gapY),
      }
    })
  })

  return { layers, positions, nodeW, nodeH, maxDepth }
}

export default function DAGVisualization({ steps = [], stepStatuses = {}, lang = 'en' }) {
  const { positions, nodeW = 180, nodeH = 72, maxDepth = 0 } = useMemo(() => layoutDAG(steps), [steps])

  if (!steps.length) {
    return (
      <div style={{
        padding: 48, textAlign: 'center', color: '#9CA3AF', fontSize: 14,
      }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" strokeWidth="1.5" strokeLinecap="round" style={{ margin: '0 auto 12px' }}>
          <path d="M4 6h16M4 12h8m-8 6h16" />
        </svg>
        {lang === 'es' ? 'No hay pasos definidos en el DAG' : 'No steps defined in the DAG'}
      </div>
    )
  }

  const gapX = 60
  const svgW = (maxDepth + 1) * (nodeW + gapX)
  const allY = Object.values(positions).map((p) => p.y)
  const minY = Math.min(...allY)
  const maxY = Math.max(...allY) + nodeH
  const svgH = maxY - minY + 48
  const offsetY = -minY + 24

  const statusIcon = (status) => {
    if (status === 'completed') return '✓'
    if (status === 'running') return '⟳'
    if (status === 'failed') return '✕'
    return null
  }

  return (
    <div style={{ overflowX: 'auto', padding: '20px 0' }}>
      <svg width={svgW + 40} height={svgH} style={{ display: 'block', margin: '0 auto' }}>
        <defs>
          <filter id="dagShadow" x="-10%" y="-10%" width="120%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#000" floodOpacity="0.06" />
          </filter>
          <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(99,102,241,0.15)" />
            <stop offset="100%" stopColor="rgba(99,102,241,0.4)" />
          </linearGradient>
        </defs>
        <g transform={`translate(20, ${offsetY})`}>
          {/* Edges */}
          {steps.map((step) =>
            (step.depends_on || []).map((dep) => {
              const from = positions[dep]
              const to = positions[step.name]
              if (!from || !to) return null
              const x1 = from.x + nodeW
              const y1 = from.y + nodeH / 2
              const x2 = to.x
              const y2 = to.y + nodeH / 2
              const cx1 = x1 + (x2 - x1) * 0.45
              const cx2 = x2 - (x2 - x1) * 0.45
              return (
                <g key={`${dep}->${step.name}`}>
                  <path
                    d={`M${x1},${y1} C${cx1},${y1} ${cx2},${y2} ${x2},${y2}`}
                    fill="none" stroke="url(#edgeGrad)" strokeWidth="2.5"
                  />
                  {/* Arrow head */}
                  <polygon
                    points={`${x2},${y2} ${x2 - 8},${y2 - 4} ${x2 - 8},${y2 + 4}`}
                    fill="rgba(99,102,241,0.5)"
                  />
                </g>
              )
            })
          )}

          {/* Nodes */}
          {steps.map((step, i) => {
            const pos = positions[step.name]
            if (!pos) return null
            const color = getAgentColor(step.type)
            const status = stepStatuses[step.name]
            const borderColor = status === 'completed' ? '#10B981'
              : status === 'running' ? '#6366F1'
              : status === 'failed' ? '#EF4444' : '#E5E7EB'
            const bgColor = status === 'completed' ? 'rgba(16,185,129,0.04)'
              : status === 'running' ? 'rgba(99,102,241,0.04)'
              : status === 'failed' ? 'rgba(239,68,68,0.04)' : '#FFFFFF'

            return (
              <g key={step.name} filter="url(#dagShadow)">
                <rect
                  x={pos.x} y={pos.y} width={nodeW} height={nodeH}
                  rx="10" fill={bgColor}
                  stroke={borderColor} strokeWidth="1.5"
                />
                {/* Color accent bar */}
                <rect
                  x={pos.x} y={pos.y} width={5} height={nodeH}
                  rx="3" fill={color}
                />
                {/* Step number badge */}
                <circle
                  cx={pos.x + nodeW - 14} cy={pos.y + 14} r="10"
                  fill={color} opacity="0.15"
                />
                <text
                  x={pos.x + nodeW - 14} y={pos.y + 18}
                  fill={color} fontSize="10" fontWeight="700"
                  fontFamily="Inter, sans-serif" textAnchor="middle"
                >
                  {i + 1}
                </text>
                {/* Name */}
                <text
                  x={pos.x + 16} y={pos.y + 28}
                  fill="#111827" fontSize="13" fontWeight="600"
                  fontFamily="Inter, sans-serif"
                >
                  {step.name.length > 18 ? step.name.slice(0, 16) + '…' : step.name}
                </text>
                {/* Type */}
                <text
                  x={pos.x + 16} y={pos.y + 46}
                  fill="#9CA3AF" fontSize="11"
                  fontFamily="Inter, sans-serif"
                >
                  {step.type || 'custom'}
                </text>
                {/* Status icon */}
                {status && (
                  <text
                    x={pos.x + 16} y={pos.y + 64}
                    fill={borderColor} fontSize="11" fontWeight="600"
                    fontFamily="Inter, sans-serif"
                  >
                    {statusIcon(status)} {status}
                  </text>
                )}
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
