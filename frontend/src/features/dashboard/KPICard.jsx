import { useState, useEffect } from 'react'

function AnimatedValue({ value, duration = 800 }) {
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    if (typeof value !== 'number') { setDisplayed(value); return }
    let start = 0
    const step = value / (duration / 16)
    const timer = setInterval(() => {
      start += step
      if (start >= value) {
        setDisplayed(value)
        clearInterval(timer)
      } else {
        setDisplayed(Math.floor(start))
      }
    }, 16)
    return () => clearInterval(timer)
  }, [value, duration])

  return <span>{typeof displayed === 'number' ? displayed.toLocaleString() : displayed}</span>
}

export default function KPICard({ icon, value, label, trend }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: '#FFFFFF',
        borderRadius: 12,
        padding: '24px 20px',
        border: hovered
          ? '1px solid rgba(37,99,235,0.3)'
          : '1px solid #E5E7EB',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        boxShadow: hovered ? '0 4px 12px rgba(0,0,0,0.06)' : '0 1px 2px rgba(0,0,0,0.04)',
        flex: '1 1 220px',
        minWidth: 200,
        animation: 'fadeIn 0.3s ease-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(37,99,235,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#2563EB',
        }}>
          {icon}
        </div>
        {trend !== undefined && (
          <span style={{
            fontSize: 12, fontWeight: 500,
            color: trend >= 0 ? '#059669' : '#DC2626',
          }}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div style={{
        fontSize: 28, fontWeight: 700, color: '#111827',
        marginBottom: 4, animation: 'countUp 0.4s ease-out',
      }}>
        <AnimatedValue value={value} />
      </div>
      <div style={{ fontSize: 13, color: '#9CA3AF' }}>{label}</div>
    </div>
  )
}
