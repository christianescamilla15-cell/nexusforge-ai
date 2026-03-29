import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
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

export default function DashboardPage({ lang = 'en' }) {
  const [isMobile, setIsMobile] = useState(false)
  const [runs, setRuns] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    Promise.all([
      fetch('/api/runs').then(r => r.json()),
      fetch('/api/runs/reliability/health').then(r => r.json()),
    ]).then(([runsData, healthData]) => {
      setRuns(runsData.runs || [])
      setHealth(healthData)
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

  const hasData = runs.length > 0 || health

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
        {!hasData && (
          <span style={{
            padding: '4px 12px', borderRadius: 6, fontSize: 12,
            background: 'rgba(37,99,235,0.06)', color: '#2563EB',
            border: '1px solid rgba(37,99,235,0.15)',
            fontWeight: 500,
          }}>
            Sin datos aun
          </span>
        )}
      </div>

      {/* KPI Cards */}
      <div className="nxf-kpi-grid" data-tour="dashboard-kpis" style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
        gap: isMobile ? 10 : 16,
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
      <div style={{
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
    </div>
  )
}
