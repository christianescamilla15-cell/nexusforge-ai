import { useState, useEffect, useRef } from 'react'

function AnimatedValue({ value, duration = 1000 }) {
  const [displayed, setDisplayed] = useState(0)
  const startTime = useRef(null)
  const animRef = useRef(null)

  useEffect(() => {
    if (typeof value !== 'number') { setDisplayed(value); return }

    const from = 0
    const to = value

    const easeOut = (t) => 1 - Math.pow(1 - t, 3) // cubic ease-out

    const animate = (timestamp) => {
      if (!startTime.current) startTime.current = timestamp
      const elapsed = timestamp - startTime.current
      const progress = Math.min(elapsed / duration, 1)
      const eased = easeOut(progress)
      setDisplayed(Math.round(from + (to - from) * eased))
      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate)
      }
    }

    startTime.current = null
    animRef.current = requestAnimationFrame(animate)
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current) }
  }, [value, duration])

  return <span>{typeof displayed === 'number' ? displayed.toLocaleString() : displayed}</span>
}

export default function KPICard({ icon, value, label, trend }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className="nxf-card-hover"
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
            display: 'flex', alignItems: 'center', gap: 2,
          }}>
            {trend >= 0 ? '\u2191' : '\u2193'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div style={{
        fontSize: 28, fontWeight: 700, color: '#111827',
        marginBottom: 4,
      }}>
        <AnimatedValue value={value} />
      </div>
      <div style={{ fontSize: 13, color: '#9CA3AF' }}>{label}</div>
    </div>
  )
}
