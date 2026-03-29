import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import SwarmCard from './SwarmCard'
import SwarmExecuteModal from './SwarmExecuteModal'

const TOPOLOGIES = ['sequential', 'parallel', 'hierarchical', 'debate', 'consensus', 'adaptive']

export default function SwarmListPage({ lang = 'en' }) {
  const [executing, setExecuting] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t('swarms', lang)}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {t('swarmSubtitle', lang)}
          <span style={{ marginLeft: 8, color: '#6366F1' }}>{TOPOLOGIES.length} {t('topologies', lang)}</span>
        </p>
      </div>

      <div data-tour="swarm-grid" style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
      }}>
        {TOPOLOGIES.map((topology) => (
          <SwarmCard key={topology} topology={topology} onExecute={(top) => setExecuting(top)} />
        ))}
      </div>

      {executing && (
        <SwarmExecuteModal topology={executing} onClose={() => setExecuting(null)} lang={lang} />
      )}
    </div>
  )
}
