import { useState, useEffect } from 'react'
import Sparkline from '../../../shared/components/Sparkline'

export default function StatsBar({ stats, lang }) {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  if (!stats || stats.length === 0) return null

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: isMobile
        ? 'repeat(2, 1fr)'
        : `repeat(${Math.min(stats.length, 4)}, 1fr)`,
      gap: 12,
      marginBottom: 24,
    }}>
      {stats.map((s, i) => (
        <div key={i} style={{
          padding: '14px 16px',
          borderRadius: 12,
          background: `${s.color || '#6366F1'}0d`,
          border: `1px solid ${s.color || '#6366F1'}22`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, fontWeight: 500 }}>
                {s.label}
              </div>
              <div style={{
                fontSize: isMobile ? 18 : 22,
                fontWeight: 700,
                color: s.color || '#6366F1',
              }}>
                {s.value}
              </div>
            </div>
            {s.sparkline && s.sparkline.length > 1 && (
              <Sparkline data={s.sparkline} color={s.color || '#6366F1'} width={80} height={28} />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
