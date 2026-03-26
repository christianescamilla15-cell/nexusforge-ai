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
        background: '#161E2E',
        borderRadius: 12,
        padding: '24px 20px',
        border: hovered
          ? '1px solid rgba(99,102,241,0.3)'
          : '1px solid rgba(255,255,255,0.06)',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        boxShadow: hovered ? '0 0 20px rgba(99,102,241,0.08)' : 'none',
        flex: '1 1 220px',
        minWidth: 200,
        animation: 'fadeIn 0.3s ease-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(99,102,241,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#818CF8',
        }}>
          {icon}
        </div>
        {trend !== undefined && (
          <span style={{
            fontSize: 12, fontWeight: 500,
            color: trend >= 0 ? '#10B981' : '#EF4444',
          }}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div style={{
        fontSize: 28, fontWeight: 700, color: '#E5E7EB',
        marginBottom: 4, animation: 'countUp 0.4s ease-out',
      }}>
        <AnimatedValue value={value} />
      </div>
      <div style={{ fontSize: 13, color: '#9CA3AF' }}>{label}</div>
    </div>
  )
}
