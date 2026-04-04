/**
 * Tiny SVG sparkline chart. No dependencies.
 * Usage: <Sparkline data={[3, 7, 2, 9, 4]} color="#6366F1" />
 */
export default function Sparkline({ data = [], width = 120, height = 32, color = '#6366F1', fillOpacity = 0.1 }) {
  if (!data.length) return null
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const step = width / Math.max(data.length - 1, 1)

  const points = data.map((v, i) => {
    const x = i * step
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')

  const fillPoints = `0,${height} ${points} ${width},${height}`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      <polygon points={fillPoints} fill={color} fillOpacity={fillOpacity} />
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* Last point dot */}
      {data.length > 0 && (() => {
        const lastX = (data.length - 1) * step
        const lastY = height - ((data[data.length - 1] - min) / range) * (height - 4) - 2
        return <circle cx={lastX} cy={lastY} r="2.5" fill={color} />
      })()}
    </svg>
  )
}
