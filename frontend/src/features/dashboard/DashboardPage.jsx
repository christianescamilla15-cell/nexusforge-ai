import { useState, useEffect } from 'react'
import { useAPI } from '../../shared/hooks/useAPI'
import KPICard from './KPICard'
import RecentRuns from './RecentRuns'
import AgentActivity from './AgentActivity'
import LoadingSpinner from '../../shared/components/LoadingSpinner'

// Demo data for when API is unreachable
const DEMO_KPIS = { workflows: 12, activeRuns: 3, agentsOnline: 5, documents: 847 }
const DEMO_RUNS = [
  { id: 1, status: 'completed', workflow: 'Analisis de Documentos', started: 'Hace 5 min', duration: '2m 14s', cost: '0.23', steps: 4 },
  { id: 2, status: 'running', workflow: 'Clasificacion de Datos', started: 'Hace 12 min', duration: '8m 02s', cost: '0.67', steps: 6 },
  { id: 3, status: 'completed', workflow: 'Resumen Ejecutivo', started: 'Hace 1h', duration: '45s', cost: '0.08', steps: 2 },
  { id: 4, status: 'failed', workflow: 'Extraccion de Entidades', started: 'Hace 2h', duration: '1m 33s', cost: '0.15', steps: 3 },
  { id: 5, status: 'completed', workflow: 'Pipeline RAG', started: 'Hace 3h', duration: '3m 50s', cost: '0.41', steps: 5 },
  { id: 6, status: 'cancelled', workflow: 'Traduccion Masiva', started: 'Hace 4h', duration: '12s', cost: '0.02', steps: 1 },
  { id: 7, status: 'completed', workflow: 'Generacion de Reportes', started: 'Hace 5h', duration: '1m 22s', cost: '0.19', steps: 3 },
  { id: 8, status: 'completed', workflow: 'Analisis de Sentimiento', started: 'Hace 6h', duration: '55s', cost: '0.11', steps: 2 },
  { id: 9, status: 'pending', workflow: 'Indexacion de Docs', started: 'Hace 6h', duration: '-', cost: '0.00', steps: 0 },
  { id: 10, status: 'completed', workflow: 'Validacion de Datos', started: 'Hace 7h', duration: '2m 01s', cost: '0.28', steps: 4 },
]
const DEMO_AGENTS = [
  { name: 'Orchestrator', count: 142, color: '#6366F1', colorEnd: '#8B5CF6' },
  { name: 'Classifier', count: 98, color: '#10B981', colorEnd: '#34D399' },
  { name: 'Summarizer', count: 87, color: '#F59E0B', colorEnd: '#FBBF24' },
  { name: 'Extractor', count: 65, color: '#EF4444', colorEnd: '#F87171' },
  { name: 'Validator', count: 43, color: '#06B6D4', colorEnd: '#22D3EE' },
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

export default function DashboardPage() {
  const { data: stats, loading: statsLoading, error: statsError } = useAPI('/stats')
  const { data: runs, loading: runsLoading, error: runsError } = useAPI('/executions/recent')
  const { data: agentStats, loading: agentsLoading } = useAPI('/agents/activity')

  const kpis = stats || DEMO_KPIS
  const recentRuns = runs || DEMO_RUNS
  const agents = agentStats || DEMO_AGENTS

  const isDemo = statsError || runsError

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB' }}>Dashboard</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF', marginTop: 4 }}>
            Vista general del sistema NexusForge AI
          </p>
        </div>
        {isDemo && (
          <span style={{
            padding: '4px 12px', borderRadius: 6, fontSize: 12,
            background: 'rgba(245,158,11,0.1)', color: '#F59E0B',
            border: '1px solid rgba(245,158,11,0.2)',
          }}>
            Modo demo — API no disponible
          </span>
        )}
      </div>

      {/* KPI Cards */}
      {statsLoading ? (
        <LoadingSpinner />
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
          <KPICard
            icon={<KPIIcon type="workflows" />}
            value={kpis.workflows}
            label="Total Workflows"
            trend={12}
          />
          <KPICard
            icon={<KPIIcon type="runs" />}
            value={kpis.activeRuns}
            label="Ejecuciones Activas"
            trend={-5}
          />
          <KPICard
            icon={<KPIIcon type="agents" />}
            value={kpis.agentsOnline}
            label="Agentes en Linea"
            trend={0}
          />
          <KPICard
            icon={<KPIIcon type="docs" />}
            value={kpis.documents}
            label="Documentos Indexados"
            trend={23}
          />
        </div>
      )}

      {/* Main content grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16, alignItems: 'start' }}>
        {/* Recent runs */}
        <div>
          {runsLoading ? <LoadingSpinner /> : <RecentRuns runs={recentRuns} />}
        </div>

        {/* Right sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {agentsLoading ? <LoadingSpinner /> : <AgentActivity agents={agents} />}

          {/* Cost overview */}
          <div style={{
            background: '#161E2E', borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.06)', padding: 20,
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB', marginBottom: 16 }}>
              Resumen de Costos
            </h3>
            {[
              { label: 'Hoy', value: '$2.14' },
              { label: 'Esta semana', value: '$18.73' },
              { label: 'Este mes', value: '$64.50' },
            ].map((item) => (
              <div key={item.label} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '10px 0',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
              }}>
                <span style={{ fontSize: 13, color: '#9CA3AF' }}>{item.label}</span>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB' }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
