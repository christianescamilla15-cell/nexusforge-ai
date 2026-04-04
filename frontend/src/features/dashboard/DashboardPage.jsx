import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'
import KPICard from './KPICard'
import RecentRuns from './RecentRuns'
import AgentActivity from './AgentActivity'

// Color palette for agent activity bars
const AGENT_COLORS = [
  { color: '#2563EB', colorEnd: '#60A5FA' },
  { color: '#059669', colorEnd: '#34D399' },
  { color: '#D97706', colorEnd: '#FBBF24' },
  { color: '#DC2626', colorEnd: '#F87171' },
  { color: '#0891B2', colorEnd: '#22D3EE' },
  { color: '#7C3AED', colorEnd: '#A78BFA' },
  { color: '#DB2777', colorEnd: '#F472B6' },
]

function KPIIcon({ type }) {
  const paths = {
    workflows: 'M4 6h16M4 12h8m-8 6h16',
    runs: 'M13 10V3L4 14h7v7l9-11h-7z',
    agents: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5',
    docs: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[type]} />
    </svg>
  )
}

export default function DashboardPage({ lang = 'en', onNavigate }) {
  const [isMobile, setIsMobile] = useState(false)
  const [runs, setRuns] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isDemo, setIsDemo] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    Promise.all([
      fetchAPI('/runs/'),
      fetchAPI('/runs/reliability/health'),
    ]).then(([runsResult, healthResult]) => {
      // Check for errors in Real mode
      if (runsResult.error || healthResult.error) {
        setError(runsResult.error || healthResult.error)
        setLoading(false)
        return
      }
      setRuns(runsResult.data?.runs || [])
      setHealth(healthResult.data)
      setIsDemo(runsResult.isDemo || healthResult.isDemo)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Map health data to KPI values
  const kpis = health
    ? {
        totalRuns: health.total_runs ?? 0,
        successRate: health.system_success_rate != null
          ? `${(health.system_success_rate * 100).toFixed(1)}%`
          : '—',
        agentsTracked: health.total_agents_tracked ?? 0,
        failedRuns: health.failed_runs ?? 0,
      }
    : { totalRuns: 0, successRate: '—', agentsTracked: 0, failedRuns: 0 }

  // Map health.agents to the shape AgentActivity expects
  const agents = (health?.agents || []).map((a, i) => ({
    name: a.agent,
    count: a.executions,
    ...AGENT_COLORS[i % AGENT_COLORS.length],
  }))

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <span style={{ fontSize: 14, color: '#9CA3AF' }}>Loading dashboard...</span>
      </div>
    )
  }

  const hasData = (runs.length > 0) || (health && (health.total_runs > 0 || health.total_agents_tracked > 0))

  const primaryButtonStyle = {
    padding: '12px 28px', borderRadius: 10, border: 'none',
    background: 'linear-gradient(135deg, #6366F1, #818CF8)',
    color: '#fff', fontSize: 15, fontWeight: 700,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
    boxShadow: '0 4px 14px rgba(99,102,241,0.3)',
    transition: 'all 0.2s',
  }
  const secondaryButtonStyle = {
    padding: '12px 28px', borderRadius: 10, border: '2px solid #E5E7EB',
    background: '#fff', color: '#374151', fontSize: 15, fontWeight: 600,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
    transition: 'all 0.2s',
  }
  const quickCardStyle = {
    padding: '20px 16px', borderRadius: 14, border: '1px solid #E5E7EB',
    background: '#fff', cursor: 'pointer', textAlign: 'center',
    transition: 'all 0.2s',
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 24, flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827' }}>
            {t('dashboard', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF', marginTop: 4 }}>
            {t('dashboardSubtitle', lang)}
          </p>
        </div>
        {isDemo && (
          <span style={{
            padding: '4px 12px', borderRadius: 6, fontSize: 12,
            background: 'rgba(245,158,11,0.08)', color: '#D97706',
            border: '1px solid rgba(245,158,11,0.2)',
            fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#D97706' }} />
            {lang === 'es' ? 'Modo Demo' : 'Demo Mode'}
          </span>
        )}
      </div>

      {/* Error banner for Real mode failures */}
      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
          color: '#991B1B', fontSize: 14, lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <span style={{ flexShrink: 0, fontSize: 16 }}>{'\u274C'}</span>
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Empty state — shown when no data */}
      {!hasData && !isDemo && !error && (
        <div style={{
          textAlign: 'center', padding: isMobile ? '40px 16px' : '60px 20px',
          background: '#fff', borderRadius: 20, border: '1px solid #E5E7EB',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          <span style={{ fontSize: 64, display: 'block', marginBottom: 16 }}>🚀</span>
          <h2 style={{ fontSize: isMobile ? 22 : 28, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
            {lang === 'es' ? '!Bienvenido a NexusForge!' : 'Welcome to NexusForge!'}
          </h2>
          <p style={{ fontSize: 16, color: '#6B7280', marginBottom: 0, maxWidth: 500, margin: '0 auto', lineHeight: 1.6 }}>
            {lang === 'es'
              ? 'Crea tu primera automatizacion en menos de 1 minuto'
              : 'Create your first automation in less than 1 minute'}
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 32, flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigate && onNavigate('wizard')}
              style={primaryButtonStyle}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'none'}
            >
              {'✨'} {lang === 'es' ? 'Crear con AI Wizard' : 'Create with AI Wizard'}
            </button>
            <button
              onClick={() => onNavigate && onNavigate('automations')}
              style={secondaryButtonStyle}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.color = '#6366F1' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#374151' }}
            >
              {'📋'} {lang === 'es' ? 'Usar una plantilla' : 'Use a template'}
            </button>
          </div>

          {/* Quick-select cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12, marginTop: 40, maxWidth: 800, margin: '40px auto 0',
          }}>
            {[
              { icon: '🎫', title: 'Ticket Triage', desc: lang === 'es' ? 'Clasificar tickets por urgencia' : 'Classify tickets by urgency' },
              { icon: '📄', title: 'Document Analyzer', desc: lang === 'es' ? 'Extraer datos de PDFs' : 'Extract data from PDFs' },
              { icon: '📧', title: 'Email Responder', desc: lang === 'es' ? 'Responder emails automaticamente' : 'Auto-respond to emails' },
              { icon: '📊', title: 'Report Generator', desc: lang === 'es' ? 'Generar reportes ejecutivos' : 'Generate executive reports' },
            ].map(card => (
              <div
                key={card.title}
                onClick={() => onNavigate && onNavigate('wizard')}
                style={quickCardStyle}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366F1'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(99,102,241,0.1)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.boxShadow = 'none' }}
              >
                <span style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>{card.icon}</span>
                <strong style={{ fontSize: 14, color: '#111827', display: 'block', marginBottom: 4 }}>{card.title}</strong>
                <p style={{ fontSize: 12, color: '#9CA3AF', margin: 0, lineHeight: 1.4 }}>{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards — only when there IS data */}
      {(hasData || isDemo) && (
        <>
          <div className="nxf-kpi-grid" data-tour="dashboard-kpis" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(200px, 100%), 1fr))',
            gap: 16,
            marginBottom: 24,
          }}>
            <KPICard
              icon={<KPIIcon type="runs" />}
              value={kpis.totalRuns}
              label="Ejecuciones Totales"
            />
            <KPICard
              icon={<KPIIcon type="workflows" />}
              value={kpis.successRate}
              label="Tasa de Exito"
            />
            <KPICard
              icon={<KPIIcon type="agents" />}
              value={kpis.agentsTracked}
              label="Agentes Rastreados"
            />
            <KPICard
              icon={<KPIIcon type="docs" />}
              value={kpis.failedRuns}
              label="Ejecuciones Fallidas"
            />
          </div>

          {/* Main content grid */}
          <div className="nxf-two-col-grid" style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 380px',
            gap: 16,
            alignItems: 'start',
          }}>
            {/* Recent runs */}
            <div style={{ overflowX: 'auto' }}>
              <RecentRuns runs={runs} />
            </div>

            {/* Right sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <AgentActivity agents={agents} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
