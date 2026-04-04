/**
 * Tiny SVG bar chart. No dependencies.
 * Usage: <MiniBarChart data={[{label:'Mon',value:5},{label:'Tue',value:12}]} />
 */
export default function MiniBarChart({ data = [], height = 80, color = '#6366F1', lang = 'en' }) {
  if (!data.length) return null
  const max = Math.max(...data.map(d => d.value), 1)
  const barWidth = Math.max(8, Math.min(24, Math.floor(280 / data.length) - 4))
  const width = data.length * (barWidth + 4) + 8

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height + 20}`} style={{ display: 'block', maxWidth: 320 }}>
        {data.map((d, i) => {
          const barH = Math.max(2, (d.value / max) * (height - 10))
          const x = i * (barWidth + 4) + 4
          const y = height - barH
          return (
            <g key={i}>
              <rect x={x} y={y} width={barWidth} height={barH} rx={3} fill={color} fillOpacity={0.8}>
                <title>{d.label}: {d.value}</title>
              </rect>
              <text x={x + barWidth / 2} y={height + 12} textAnchor="middle" fontSize="8" fill="#9CA3AF">
                {d.label}
              </text>
              {d.value > 0 && (
                <text x={x + barWidth / 2} y={y - 3} textAnchor="middle" fontSize="8" fill="#6B7280" fontWeight="600">
                  {d.value}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
