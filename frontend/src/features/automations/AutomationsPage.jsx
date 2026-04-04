import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import PublishModal from './PublishModal'
import RunInputModal from './RunInputModal'
import TemplatesLibrary from '../templates/TemplatesLibrary'
import { useToast } from '../../shared/hooks/useToast'
import { addNotification } from '../../shared/components/NotificationBell'

const TRIGGER_BADGE = {
  manual: { en: 'Manual', es: 'Manual', color: '#6366F1', bg: 'rgba(99,102,241,0.1)' },
  schedule: { en: 'Scheduled', es: 'Programado', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  webhook: { en: 'Webhook', es: 'Webhook', color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
}

function AutomationCard({ auto, lang, onRun, onDelete, onDashboard, running }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const trigger = TRIGGER_BADGE[auto.trigger_type] || TRIGGER_BADGE.manual
  const bg = auto.color ? `${auto.color}12` : 'rgba(99,102,241,0.08)'

  return (
    <div style={{
      background: '#fff', borderRadius: 16, border: '1px solid #E5E7EB',
      padding: 24, transition: 'all 0.2s', position: 'relative',
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = auto.color || '#6366F1'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div style={{
          width: 52, height: 52, borderRadius: 14, background: bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26,
        }}>
          {auto.icon}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            background: trigger.bg, color: trigger.color,
          }}>
            {trigger[lang]}
          </span>
          <div style={{ position: 'relative' }}>
            <button onClick={() => setMenuOpen(m => !m)} style={{
              background: '#F3F4F6', border: 'none', borderRadius: 6, width: 28, height: 28,
              cursor: 'pointer', fontSize: 16, color: '#9CA3AF', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>&#x22EE;</button>
            {menuOpen && (
              <div onClick={e => e.stopPropagation()} style={{
                position: 'absolute', right: 0, top: 32, width: 160, zIndex: 50,
                background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10,
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4,
              }}>
                {[
                  { label: lang === 'es' ? 'Dashboard' : 'Dashboard', icon: '\uD83D\uDCCA', action: () => { onDashboard(auto.id); setMenuOpen(false) } },
                  { label: lang === 'es' ? 'Despublicar' : 'Unpublish', icon: '\uD83D\uDDD1\uFE0F', action: () => { onDelete(auto.id); setMenuOpen(false) }, color: '#EF4444' },
                ].map((item, i) => (
                  <div key={i} onClick={item.action} style={{
                    padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
                    display: 'flex', alignItems: 'center', gap: 8, color: item.color || '#374151',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span>{item.icon}</span>{item.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <h3 onClick={() => onDashboard(auto.id)} style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 6, cursor: 'pointer' }}
        onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
        onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
      >{auto.name}</h3>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, marginBottom: 14, minHeight: 36 }}>
        {auto.description || auto.workflow_name}
      </p>

      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#9CA3AF', marginBottom: 16 }}>
        <span>&#x1F504; {auto.total_runs} {lang === 'es' ? 'ejecuciones' : 'runs'}</span>
        {auto.last_run_at && (
          <span>&#x1F550; {new Date(auto.last_run_at).toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US')}</span>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 12, borderTop: '1px solid #F3F4F6' }}>
        <span style={{ fontSize: 12, color: '#9CA3AF' }}>{auto.workflow_name}</span>
        <button onClick={() => onRun(auto)} disabled={running === auto.id} style={{
          padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600,
          background: running === auto.id ? '#A5B4FC' : `linear-gradient(135deg, ${auto.color || '#6366F1'}, ${auto.color || '#8B5CF6'})`,
          color: '#fff', cursor: running === auto.id ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {running === auto.id ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
              <path d="M21 12a9 9 0 11-6.219-8.56" />
            </svg>
          ) : '\u25B6'}
          {running === auto.id
            ? (lang === 'es' ? 'Ejecutando...' : 'Running...')
            : (lang === 'es' ? 'Ejecutar' : 'Run')}
        </button>
      </div>
    </div>
  )
}

export default function AutomationsPage({ lang = 'en', onNavigateToExecution, initialDashboardId = null, onOpenDashboard }) {
  const [isMobile, setIsMobile] = useState(false)
  const [userAutomations, setUserAutomations] = useState([])
  const [loadingUser, setLoadingUser] = useState(true)
  const [showPublish, setShowPublish] = useState(false)
  const [running, setRunning] = useState(null)
  const [runInputTarget, setRunInputTarget] = useState(null)
  const toast = useToast()

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // If initialDashboardId is set, open it immediately
  useEffect(() => {
    if (initialDashboardId && onOpenDashboard) {
      onOpenDashboard(initialDashboardId)
    }
  }, [initialDashboardId, onOpenDashboard])

  const loadUserAutomations = () => {
    setLoadingUser(true)
    fetchAPI('/automations/').then(res => {
      if (!res.error && Array.isArray(res.data)) setUserAutomations(res.data)
      setLoadingUser(false)
    })
  }

  useEffect(() => { loadUserAutomations() }, [])

  const handleRun = async (auto) => {
    const inputType = auto.input_config?.type || 'none'
    if (inputType !== 'none') {
      setRunInputTarget(auto)
      return
    }
    await _executeRun(auto, {})
  }

  const _executeRun = async (auto, input_data) => {
    setRunning(auto.id)
    toast.show(
      lang === 'es' ? '\uD83D\uDE80 Ejecutando automatizacion...' : '\uD83D\uDE80 Running automation...',
      'info'
    )
    const res = await fetchAPI(`/automations/${auto.id}/run`, {
      method: 'POST',
      body: JSON.stringify({ input_data }),
    })
    setRunning(null)
    if (!res.error && res.data?.run_id && onNavigateToExecution) {
      onNavigateToExecution(res.data.run_id)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm(lang === 'es' ? '\u00BFDespublicar esta automatizacion?' : 'Unpublish this automation?')) return
    await fetchAPI(`/automations/${id}`, { method: 'DELETE' })
    setUserAutomations(prev => prev.filter(a => a.id !== id))
  }

  const handleOpenDashboard = (id) => {
    if (onOpenDashboard) {
      onOpenDashboard(id)
    }
  }

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: 20,
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Automatizaciones' : 'Automations'}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Flujos en produccion listos para ejecutar. Publica tus propios workflows como automatizaciones.'
            : 'Production-ready workflows. Publish your own workflows as automations.'}
        </p>
      </div>

      {/* Templates */}
      <TemplatesLibrary lang={lang} isMobile={isMobile} onDeployed={(data) => {
        loadUserAutomations()
        if (data?.automation_id && onOpenDashboard) {
          onOpenDashboard(data.automation_id)
        }
      }} />

      {/* User automations */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
          {lang === 'es' ? 'Mis Automatizaciones' : 'My Automations'}
        </p>
        <button onClick={() => setShowPublish(true)} style={{
          padding: '7px 14px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600,
          background: 'linear-gradient(135deg, #6366F1, #8B5CF6)', color: '#fff', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ fontSize: 16 }}>+</span>
          {lang === 'es' ? 'Publicar' : 'Publish'}
        </button>
      </div>

      {loadingUser ? (
        <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
          {lang === 'es' ? 'Cargando...' : 'Loading...'}
        </div>
      ) : userAutomations.length === 0 ? (
        <div onClick={() => setShowPublish(true)} style={{
          padding: 32, borderRadius: 14, border: '2px dashed #E5E7EB',
          textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.15s',
        }}
          onMouseEnter={e => e.currentTarget.style.borderColor = '#6366F1'}
          onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
        >
          <span style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>+</span>
          <p style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', margin: 0 }}>
            {lang === 'es' ? 'Publica tu primer workflow como automatizacion' : 'Publish your first workflow as an automation'}
          </p>
          <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
            {lang === 'es' ? 'Crea un workflow en el Builder y publicalo aqui.' : 'Create a workflow in the Builder and publish it here.'}
          </p>
        </div>
      ) : (
        <div style={gridStyle}>
          {userAutomations.map(auto => (
            <AutomationCard key={auto.id} auto={auto} lang={lang} onRun={handleRun} onDelete={handleDelete} onDashboard={handleOpenDashboard} running={running} />
          ))}
          <div onClick={() => setShowPublish(true)} style={{
            padding: 24, borderRadius: 16, border: '2px dashed #E5E7EB',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', minHeight: 180, transition: 'border-color 0.15s',
          }}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#6366F1'}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
          >
            <span style={{ fontSize: 28, marginBottom: 8 }}>+</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#9CA3AF' }}>
              {lang === 'es' ? 'Publicar otra' : 'Publish another'}
            </span>
          </div>
        </div>
      )}

      {showPublish && (
        <PublishModal lang={lang} onClose={() => setShowPublish(false)} onPublished={loadUserAutomations} />
      )}

      {runInputTarget && (
        <RunInputModal
          automation={runInputTarget}
          lang={lang}
          onClose={() => setRunInputTarget(null)}
          onSubmit={(input_data) => {
            const auto = runInputTarget
            setRunInputTarget(null)
            _executeRun(auto, input_data)
          }}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
