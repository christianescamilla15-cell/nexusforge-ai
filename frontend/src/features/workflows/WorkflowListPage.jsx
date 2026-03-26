import { useState, useEffect } from 'react'
import { useAPI } from '../../shared/hooks/useAPI'
import { t } from '../../shared/i18n/translations'
import DataTable from '../../shared/components/DataTable'
import StatusBadge from '../../shared/components/StatusBadge'
import LoadingSpinner from '../../shared/components/LoadingSpinner'
import EmptyState from '../../shared/components/EmptyState'
import WorkflowCreateModal from './WorkflowCreateModal'

const DEMO_WORKFLOWS = [
  { id: 'wf-1', name: 'Analisis de Documentos', status: 'active', version: 'v1.3', created: '2026-03-20', steps: 4 },
  { id: 'wf-2', name: 'Clasificacion de Datos', status: 'active', version: 'v2.1', created: '2026-03-18', steps: 6 },
  { id: 'wf-3', name: 'Resumen Ejecutivo', status: 'draft', version: 'v1.0', created: '2026-03-22', steps: 2 },
  { id: 'wf-4', name: 'Extraccion de Entidades', status: 'paused', version: 'v1.1', created: '2026-03-15', steps: 3 },
  { id: 'wf-5', name: 'Pipeline RAG', status: 'active', version: 'v3.0', created: '2026-03-10', steps: 5 },
  { id: 'wf-6', name: 'Traduccion Masiva', status: 'archived', version: 'v1.2', created: '2026-02-28', steps: 3 },
]

export default function WorkflowListPage({ onSelectWorkflow, lang = 'en' }) {
  const { data, loading, error, refetch } = useAPI('/workflows')
  const [filter, setFilter] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const STATUS_FILTERS = [
    { key: 'all', label: t('all', lang) },
    { key: 'draft', label: t('draft', lang) },
    { key: 'active', label: t('active', lang) },
    { key: 'paused', label: t('paused', lang) },
    { key: 'archived', label: t('archived', lang) },
  ]

  const columns = [
    { key: 'name', label: t('name', lang) },
    {
      key: 'status', label: t('status', lang),
      render: (v) => {
        const map = { active: 'completed', draft: 'pending', paused: 'cancelled', archived: 'pending' }
        return <StatusBadge status={map[v] || v} />
      },
    },
    { key: 'version', label: t('version', lang) },
    { key: 'steps', label: t('steps', lang) },
    { key: 'created', label: t('created', lang) },
  ]

  const workflows = data || DEMO_WORKFLOWS
  const filtered = filter === 'all' ? workflows : workflows.filter((w) => w.status === filter)

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 24, flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#E5E7EB' }}>
            {t('workflows', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF', marginTop: 4 }}>
            {t('manageWorkflows', lang)}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          aria-label={t('newWorkflow', lang)}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: '#6366F1', color: '#fff', fontSize: 14, fontWeight: 500,
            display: 'flex', alignItems: 'center', gap: 8,
            transition: 'background 0.2s',
            width: isMobile ? '100%' : 'auto',
            justifyContent: 'center',
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#5558E6'}
          onMouseLeave={(e) => e.currentTarget.style.background = '#6366F1'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14m-7-7h14" />
          </svg>
          {t('newWorkflow', lang)}
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            aria-label={`Filter: ${f.label}`}
            style={{
              padding: '6px 14px', borderRadius: 6, fontSize: 13,
              border: '1px solid',
              borderColor: filter === f.key ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.08)',
              background: filter === f.key ? 'rgba(99,102,241,0.1)' : 'transparent',
              color: filter === f.key ? '#818CF8' : '#9CA3AF',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <LoadingSpinner />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M4 6h16M4 12h8m-8 6h16" />
            </svg>
          }
          title={t('noWorkflows', lang)}
          description={t('noWorkflowsDesc', lang)}
          actionLabel={t('createWorkflow', lang)}
          onAction={() => setShowCreate(true)}
        />
      ) : (
        <div style={{
          background: '#161E2E', borderRadius: 12,
          border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
          overflowX: 'auto',
        }}>
          <DataTable
            columns={columns}
            data={filtered}
            onRowClick={(row) => onSelectWorkflow && onSelectWorkflow(row.id)}
            pageSize={10}
          />
        </div>
      )}

      <WorkflowCreateModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={() => { setShowCreate(false); refetch() }}
      />
    </div>
  )
}
