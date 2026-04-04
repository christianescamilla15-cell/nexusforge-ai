import { useState, useEffect } from 'react'
import { fetchAPI } from '../../../services/api'
import TicketDashboard from './TicketDashboard'
import DocumentDashboard from './DocumentDashboard'
import EmailDashboard from './EmailDashboard'
import ReportDashboard from './ReportDashboard'
import GenericDashboard from './GenericDashboard'
import AutomationDashboard from '../AutomationDashboard'

function detectAutomationType(automation) {
  const steps = automation.dag_definition?.steps || []
  const types = steps.map(s => s.type)

  if (types.includes('classifier') && types.includes('router')) return 'ticket'
  if (types.includes('ocr') || (types.includes('extractor') && types.length <= 5)) return 'document'
  if (types.includes('knowledge') && types.includes('classifier')) return 'email'
  if (types.includes('analyzer') && types.includes('reporter')) return 'report'
  return 'generic'
}

const TAB_LABELS = {
  dashboard: { en: 'Dashboard', es: 'Dashboard' },
  settings: { en: 'Settings', es: 'Configuracion' },
}

export default function SmartDashboard({ automationId, lang, onBack, onRun }) {
  const [automation, setAutomation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    if (!automationId) return
    setLoading(true)
    setError(null)

    // Fetch full automation data including dag_definition
    fetchAPI(`/automations/${automationId}`).then(res => {
      if (res.error) {
        setError(res.error)
      } else if (res.data) {
        setAutomation(res.data)
      }
      setLoading(false)
    })
  }, [automationId])

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF' }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite', margin: '0 auto 12px', display: 'block' }}>
          <path d="M21 12a9 9 0 11-6.219-8.56" />
        </svg>
        {lang === 'es' ? 'Cargando dashboard...' : 'Loading dashboard...'}
        <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={onBack} style={{
          background: '#F3F4F6', border: 'none', borderRadius: 8,
          padding: '8px 16px', cursor: 'pointer', fontSize: 13,
          color: '#6B7280', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>←</span> {lang === 'es' ? 'Volver' : 'Back'}
        </button>
        <div style={{
          padding: '16px 20px', borderRadius: 10,
          background: '#FEF2F2', border: '1px solid #FECACA',
          color: '#DC2626', fontSize: 13,
        }}>
          {error}
        </div>
      </div>
    )
  }

  if (!automation) return null

  const type = detectAutomationType(automation)
  const color = automation.color || '#6366F1'

  const renderDashboard = () => {
    const props = { automation, lang, onBack }
    switch (type) {
      case 'ticket': return <TicketDashboard {...props} />
      case 'document': return <DocumentDashboard {...props} />
      case 'email': return <EmailDashboard {...props} />
      case 'report': return <ReportDashboard {...props} />
      default: return <GenericDashboard {...props} />
    }
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 0, marginBottom: 20,
        borderBottom: '2px solid #E5E7EB',
      }}>
        {Object.entries(TAB_LABELS).map(([key, labels]) => {
          const active = activeTab === key
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              style={{
                padding: isMobile ? '10px 14px' : '10px 24px',
                fontSize: 13,
                fontWeight: active ? 700 : 500,
                color: active ? color : '#6B7280',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                borderBottom: active ? `2px solid ${color}` : '2px solid transparent',
                marginBottom: -2,
                transition: 'all 0.15s',
              }}
            >
              {lang === 'es' ? labels.es : labels.en}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'dashboard' && renderDashboard()}

      {activeTab === 'settings' && (
        <AutomationDashboard
          automationId={automationId}
          lang={lang}
          onBack={onBack}
          onRun={onRun}
        />
      )}

      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
