import { useMemo } from 'react'

const AGENT_COLORS = {
  orchestrator: '#6366F1',
  classifier: '#10B981',
  summarizer: '#F59E0B',
  extractor: '#06B6D4',
  validator: '#EF4444',
  default: '#9CA3AF',
}

function getAgentColor(type) {
  return AGENT_COLORS[type] || AGENT_COLORS.default
}

function layoutDAG(steps) {
  if (!steps || !steps.length) return { layers: [], positions: {} }

  // Assign layers by topological depth
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

  const nodeW = 160
  const nodeH = 60
  const gapX = 80
  const gapY = 24
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

export default function DAGVisualization({ steps = [], stepStatuses = {} }) {
  const { positions, nodeW = 160, nodeH = 60, maxDepth = 0 } = useMemo(() => layoutDAG(steps), [steps])

  if (!steps.length) {
    return (
      <div style={{
        padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14,
      }}>
        No hay pasos definidos en el DAG
      </div>
    )
  }

  const gapX = 80
  const svgW = (maxDepth + 1) * (nodeW + gapX)
  // Find min/max y for svg height
  const allY = Object.values(positions).map((p) => p.y)
  const minY = Math.min(...allY)
  const maxY = Math.max(...allY) + nodeH
  const svgH = maxY - minY + 40
  const offsetY = -minY + 20

  return (
    <div style={{ overflowX: 'auto', padding: '16px 0' }}>
      <svg width={svgW + 40} height={svgH} style={{ display: 'block', margin: '0 auto' }}>
        <g transform={`translate(20, ${offsetY})`}>
          {/* Arrows */}
          {steps.map((step) =>
            (step.depends_on || []).map((dep) => {
              const from = positions[dep]
              const to = positions[step.name]
              if (!from || !to) return null
              const x1 = from.x + nodeW
              const y1 = from.y + nodeH / 2
              const x2 = to.x
              const y2 = to.y + nodeH / 2
              const cx1 = x1 + (x2 - x1) * 0.4
              const cx2 = x2 - (x2 - x1) * 0.4
              return (
                <g key={`${dep}->${step.name}`}>
                  <path
                    d={`M${x1},${y1} C${cx1},${y1} ${cx2},${y2} ${x2},${y2}`}
                    fill="none" stroke="rgba(99,102,241,0.3)" strokeWidth="2"
                  />
                  <circle cx={x2} cy={y2} r="3" fill="rgba(99,102,241,0.5)" />
                </g>
              )
            })
          )}

          {/* Nodes */}
          {steps.map((step) => {
            const pos = positions[step.name]
            if (!pos) return null
            const color = getAgentColor(step.type)
            const status = stepStatuses[step.name]
            const statusColor = status === 'completed' ? '#10B981'
              : status === 'running' ? '#6366F1'
              : status === 'failed' ? '#EF4444' : '#E5E7EB'
            return (
              <g key={step.name}>
                <rect
                  x={pos.x} y={pos.y} width={nodeW} height={nodeH}
                  rx="8" fill="#FFFFFF"
                  stroke={statusColor} strokeWidth="2"
                />
                {/* Type indicator bar */}
                <rect
                  x={pos.x} y={pos.y} width={4} height={nodeH}
                  rx="2" fill={color}
                />
                <text
                  x={pos.x + 16} y={pos.y + 24}
                  fill="#111827" fontSize="13" fontWeight="500"
                  fontFamily="Inter, sans-serif"
                >
                  {step.name}
                </text>
                <text
                  x={pos.x + 16} y={pos.y + 44}
                  fill="#9CA3AF" fontSize="11"
                  fontFamily="Inter, sans-serif"
                >
                  {step.type || 'custom'}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
