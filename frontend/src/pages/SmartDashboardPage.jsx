import { useState, useEffect } from 'react'
import { fetchAPI } from '../services/api'
import SmartDashboard from '../features/automations/dashboards/SmartDashboard'

export default function SmartDashboardPage({ automationId, onBack, onRun, lang }) {
  const [automationName, setAutomationName] = useState('')
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    if (!automationId) return
    fetchAPI(`/automations/${automationId}`).then(res => {
      if (!res.error && res.data?.name) {
        setAutomationName(res.data.name)
      }
    })
  }, [automationId])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Breadcrumb */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginBottom: 20, flexWrap: 'wrap',
      }}>
        <button
          onClick={onBack}
          style={{
            background: '#F3F4F6', border: 'none', borderRadius: 8,
            width: 36, height: 36, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#6B7280', flexShrink: 0,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>

        <nav style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: isMobile ? 12 : 13, color: '#9CA3AF',
        }}>
          <span
            onClick={onBack}
            style={{ cursor: 'pointer', color: '#6366F1', fontWeight: 500 }}
            onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
            onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
          >
            {lang === 'es' ? 'Automatizaciones' : 'Automations'}
          </span>
          <span style={{ color: '#D1D5DB' }}>/</span>
          <span style={{ color: '#374151', fontWeight: 600 }}>
            {automationName || (lang === 'es' ? 'Cargando...' : 'Loading...')}
          </span>
        </nav>
      </div>

      {/* Full-width dashboard */}
      <SmartDashboard
        automationId={automationId}
        lang={lang}
        onBack={onBack}
        onRun={onRun}
      />

      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
