import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import PublishModal from './PublishModal'
import RunInputModal from './RunInputModal'
import AutomationDashboard from './AutomationDashboard'
import TemplatesLibrary from '../templates/TemplatesLibrary'

const PREBUILT = [
  {
    key: 'analyze', icon: '🔍', color: '#8B5CF6', bg: 'rgba(139,92,246,0.08)', agents: 4,
    name: { en: 'AI Analyze', es: 'IA Analizar' },
    desc: { en: 'Upload documents or connect Google Drive — AI extracts entities, summarizes, and sends results via email.', es: 'Sube documentos o conecta Google Drive — la IA extrae entidades, resume y envía resultados por email.' },
    tags: { en: ['RAG', 'Upload', 'Drive', 'Email'], es: ['RAG', 'Subida', 'Drive', 'Email'] },
  },
  {
    key: 'enterprise-ops', icon: '🏢', color: '#6366F1', bg: 'rgba(99,102,241,0.08)', agents: 8,
    name: { en: 'Enterprise Ops', es: 'Ops Empresariales' },
    desc: { en: 'Multi-agent pipeline: intake, classify intent, CRM update, email, scheduling, notifications.', es: 'Pipeline multi-agente: recepción, clasificación de intención, actualización CRM, email, agenda, notificaciones.' },
    tags: { en: ['CRM', 'Email', 'Scheduling', 'Supervisor'], es: ['CRM', 'Email', 'Agenda', 'Supervisor'] },
  },
  {
    key: 'documents', icon: '📄', color: '#2563EB', bg: 'rgba(37,99,235,0.08)', agents: 3,
    name: { en: 'Document Intelligence', es: 'Inteligencia Documental' },
    desc: { en: 'RAG pipeline: upload documents, chunk & embed, then query with semantic search and summarization.', es: 'Pipeline RAG: sube documentos, fragmenta e indexa, luego consulta con búsqueda semántica y resumen.' },
    tags: { en: ['RAG', 'Embeddings', 'Summary', 'NER'], es: ['RAG', 'Embeddings', 'Resumen', 'NER'] },
  },
  {
    key: 'playground', icon: '⚡', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', agents: 0,
    name: { en: 'Playground', es: 'Playground' },
    desc: { en: 'Sandbox to test any agent or chain freely with custom prompts and real-time results.', es: 'Sandbox para probar cualquier agente o cadena libremente con prompts personalizados.' },
    tags: { en: ['Sandbox', 'Custom', 'Testing'], es: ['Sandbox', 'Personalizado', 'Pruebas'] },
  },
  {
    key: 'swarms', icon: '🐝', color: '#EC4899', bg: 'rgba(236,72,153,0.08)', agents: 24,
    name: { en: 'Swarm Execution', es: 'Ejecución en Enjambre' },
    desc: { en: '6 topologies: Sequential, Parallel, Hierarchical, Debate, Consensus, Adaptive.', es: '6 topologías: Secuencial, Paralelo, Jerárquico, Debate, Consenso, Adaptativo.' },
    tags: { en: ['Sequential', 'Parallel', 'Debate', 'Consensus'], es: ['Secuencial', 'Paralelo', 'Debate', 'Consenso'] },
  },
]

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
            }}>⋮</button>
            {menuOpen && (
              <div onClick={e => e.stopPropagation()} style={{
                position: 'absolute', right: 0, top: 32, width: 160, zIndex: 50,
                background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10,
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4,
              }}>
                {[
                  { label: lang === 'es' ? 'Dashboard' : 'Dashboard', icon: '📊', action: () => { onDashboard(auto); setMenuOpen(false) } },
                  { label: lang === 'es' ? 'Despublicar' : 'Unpublish', icon: '🗑️', action: () => { onDelete(auto.id); setMenuOpen(false) }, color: '#EF4444' },
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

      <h3 onClick={() => onDashboard(auto)} style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 6, cursor: 'pointer' }}
        onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
        onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
      >{auto.name}</h3>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, marginBottom: 14, minHeight: 36 }}>
        {auto.description || auto.workflow_name}
      </p>

      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#9CA3AF', marginBottom: 16 }}>
        <span>🔄 {auto.total_runs} {lang === 'es' ? 'ejecuciones' : 'runs'}</span>
        {auto.last_run_at && (
          <span>🕐 {new Date(auto.last_run_at).toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US')}</span>
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
          ) : '▶'}
          {running === auto.id
            ? (lang === 'es' ? 'Ejecutando...' : 'Running...')
            : (lang === 'es' ? 'Ejecutar' : 'Run')}
        </button>
      </div>
    </div>
  )
}

export default function AutomationsPage({ lang = 'en', onOpenCase, onNavigateToExecution }) {
  const [isMobile, setIsMobile] = useState(false)
  const [hoveredKey, setHoveredKey] = useState(null)
  const [userAutomations, setUserAutomations] = useState([])
  const [loadingUser, setLoadingUser] = useState(true)
  const [showPublish, setShowPublish] = useState(false)
  const [running, setRunning] = useState(null)
  const [runInputTarget, setRunInputTarget] = useState(null) // automation needing input
  const [dashboardId, setDashboardId] = useState(null) // automation id for dashboard view

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

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
    if (!confirm(lang === 'es' ? '¿Despublicar esta automatización?' : 'Unpublish this automation?')) return
    await fetchAPI(`/automations/${id}`, { method: 'DELETE' })
    setUserAutomations(prev => prev.filter(a => a.id !== id))
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
            ? 'Flujos en producción listos para ejecutar. Publica tus propios workflows como automatizaciones.'
            : 'Production-ready workflows. Publish your own workflows as automations.'}
        </p>
      </div>

      {/* Pre-built */}
      <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
        {lang === 'es' ? 'Pre-construidas' : 'Pre-built'}
      </p>
      <div style={{ ...gridStyle, marginBottom: 32 }}>
        {PREBUILT.map(uc => (
          <div key={uc.key} onClick={() => onOpenCase && onOpenCase(uc.key)}
            onMouseEnter={() => setHoveredKey(uc.key)}
            onMouseLeave={() => setHoveredKey(null)}
            style={{
              background: '#fff', borderRadius: 16, padding: 24, cursor: 'pointer',
              border: `1px solid ${hoveredKey === uc.key ? uc.color : '#E5E7EB'}`,
              transition: 'all 0.2s',
              boxShadow: hoveredKey === uc.key ? `0 8px 24px ${uc.bg}` : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{ width: 52, height: 52, borderRadius: 14, background: uc.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26 }}>
                {uc.icon}
              </div>
              <span style={{ padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: 'rgba(16,185,129,0.1)', color: '#10B981' }}>
                {lang === 'es' ? 'En vivo' : 'Live'}
              </span>
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 8 }}>{uc.name[lang]}</h3>
            <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, marginBottom: 16, minHeight: 36 }}>{uc.desc[lang]}</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
              {uc.tags[lang].map(tag => (
                <span key={tag} style={{ padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500, background: uc.bg, color: uc.color }}>{tag}</span>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 12, borderTop: '1px solid #F3F4F6' }}>
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>
                {uc.agents > 0 ? `${uc.agents} ${lang === 'es' ? 'agentes' : 'agents'}` : (lang === 'es' ? 'Personalizable' : 'Customizable')}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, color: uc.color, display: 'flex', alignItems: 'center', gap: 4 }}>
                {lang === 'es' ? 'Ejecutar' : 'Run'}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M5 12h14m-7-7l7 7-7 7" /></svg>
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Templates */}
      <TemplatesLibrary lang={lang} isMobile={isMobile} onDeployed={() => loadUserAutomations()} />

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
            {lang === 'es' ? 'Publica tu primer workflow como automatización' : 'Publish your first workflow as an automation'}
          </p>
          <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
            {lang === 'es' ? 'Crea un workflow en el Builder y publícalo aquí.' : 'Create a workflow in the Builder and publish it here.'}
          </p>
        </div>
      ) : (
        <div style={gridStyle}>
          {userAutomations.map(auto => (
            <AutomationCard key={auto.id} auto={auto} lang={lang} onRun={handleRun} onDelete={handleDelete} onDashboard={(a) => setDashboardId(a.id)} running={running} />
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

      {dashboardId && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
          zIndex: 100, backdropFilter: 'blur(4px)', overflowY: 'auto', padding: '24px 16px',
        }} onClick={() => setDashboardId(null)}>
          <div onClick={e => e.stopPropagation()} style={{
            background: '#F9FAFB', borderRadius: 16, padding: 24,
            width: '100%', maxWidth: 800,
            border: '1px solid #E5E7EB', boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
          }}>
            <AutomationDashboard
              automationId={dashboardId}
              lang={lang}
              onBack={() => setDashboardId(null)}
              onRun={(auto) => { setDashboardId(null); handleRun(auto) }}
            />
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
