import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { t } from '../../shared/i18n/translations'
import { useIsMobile } from '../../shared/hooks/useIsMobile'
import SwarmCard from './SwarmCard'
import SwarmExecuteModal from './SwarmExecuteModal'

const FALLBACK_TOPOLOGIES = ['sequential', 'parallel', 'hierarchical', 'debate', 'consensus', 'adaptive']

export default function SwarmListPage({ lang = 'en' }) {
  const [executing, setExecuting] = useState(null)
  const [topologies, setTopologies] = useState(FALLBACK_TOPOLOGIES)
  const isMobile = useIsMobile()

  // Fetch real topologies from backend
  useEffect(() => {
    fetchAPI('/swarms/').then(res => {
      if (!res.error && Array.isArray(res.data?.topologies)) {
        setTopologies(res.data.topologies)
      } else if (!res.error && Array.isArray(res.data)) {
        setTopologies(res.data)
      }
    })
  }, [])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t('swarms', lang)}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {t('swarmSubtitle', lang)}
          <span style={{ marginLeft: 8, color: '#6366F1' }}>{topologies.length} {t('topologies', lang)}</span>
        </p>
      </div>

      <div data-tour="swarm-grid" style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
      }}>
        {topologies.map((topology, i) => (
          <SwarmCard
            key={typeof topology === 'string' ? topology : topology?.name || topology?.id || i}
            topology={typeof topology === 'string' ? topology : topology?.name || topology}
            onExecute={(top) => setExecuting(top)}
          />
        ))}
      </div>

      {executing && (
        <SwarmExecuteModal topology={executing} onClose={() => setExecuting(null)} lang={lang} />
      )}
    </div>
  )
}
