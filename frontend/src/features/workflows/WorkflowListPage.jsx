import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'
import DataTable from '../../shared/components/DataTable'
import StatusBadge from '../../shared/components/StatusBadge'
import EmptyState from '../../shared/components/EmptyState'
import WorkflowCreateModal from './WorkflowCreateModal'

const DEMO_WORKFLOWS = [
  { id: 'wf-1', name: 'Análisis de Documentos', status: 'active', version: 'v1.3', created: '2026-03-20', steps: 4 },
  { id: 'wf-2', name: 'Clasificación de Datos', status: 'active', version: 'v2.1', created: '2026-03-18', steps: 6 },
  { id: 'wf-3', name: 'Resumen Ejecutivo', status: 'draft', version: 'v1.0', created: '2026-03-22', steps: 2 },
  { id: 'wf-4', name: 'Extracción de Entidades', status: 'paused', version: 'v1.1', created: '2026-03-15', steps: 3 },
  { id: 'wf-5', name: 'Pipeline RAG', status: 'active', version: 'v3.0', created: '2026-03-10', steps: 5 },
  { id: 'wf-6', name: 'Traducción Masiva', status: 'archived', version: 'v1.2', created: '2026-02-28', steps: 3 },
]

export default function WorkflowListPage({ onSelectWorkflow, lang = 'en' }) {
  const [filter, setFilter] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [apiWorkflows, setApiWorkflows] = useState([])
  const [localWorkflows, setLocalWorkflows] = useState([])

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Fetch real workflows from API
  useEffect(() => {
    fetchAPI('/workflows').then((res) => {
      if (!res.error && res.data) {
        const list = Array.isArray(res.data) ? res.data : res.data.workflows || []
        setApiWorkflows(list)
      }
    })
  }, [])

  const STATUS_FILTERS = [
    { key: 'all', label: t('all', lang) },
    { key: 'draft', label: t('draft', lang) },
    { key: 'active', label: t('active', lang) },
    { key: 'paused', label: t('paused', lang) },
    { key: 'archived', label: t('archived', lang) },
  ]

  const [menuOpen, setMenuOpen] = useState(null) // workflow id that has menu open
  const [renaming, setRenaming] = useState(null) // workflow id being renamed
  const [renameValue, setRenameValue] = useState('')

  const handleDelete = async (wf) => {
    if (!confirm(lang === 'es' ? `¿Eliminar "${wf.name}"?` : `Delete "${wf.name}"?`)) return
    if (wf.id?.startsWith('wf-')) return // can't delete demos
    await fetchAPI(`/workflows/${wf.id}`, { method: 'DELETE' })
    setApiWorkflows(prev => prev.filter(w => w.id !== wf.id))
    setMenuOpen(null)
  }

  const handleRename = async (wf) => {
    if (!renameValue.trim()) return
    if (!wf.id?.startsWith('wf-')) {
      await fetchAPI(`/workflows/${wf.id}`, {
        method: 'PUT',
        body: JSON.stringify({ name: renameValue }),
      })
      setApiWorkflows(prev => prev.map(w => w.id === wf.id ? { ...w, name: renameValue } : w))
    }
    setRenaming(null)
    setMenuOpen(null)
  }

  const columns = [
    { key: 'name', label: t('name', lang), render: (v, row) => {
      if (renaming === row.id) {
        return (
          <div style={{ display: 'flex', gap: 4 }}>
            <input
              value={renameValue}
              onChange={e => setRenameValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleRename(row)}
              autoFocus
              style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #6366F1', fontSize: 13, outline: 'none', flex: 1 }}
            />
            <button onClick={() => handleRename(row)} style={{ padding: '4px 8px', borderRadius: 6, border: 'none', background: '#6366F1', color: '#fff', fontSize: 11, cursor: 'pointer' }}>OK</button>
            <button onClick={() => setRenaming(null)} style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #E5E7EB', background: '#fff', fontSize: 11, cursor: 'pointer' }}>✕</button>
          </div>
        )
      }
      return v
    }},
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
    { key: 'actions', label: '', render: (_, row) => (
      <div style={{ position: 'relative' }}>
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === row.id ? null : row.id) }}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px', fontSize: 18, color: '#9CA3AF' }}
        >
          ⋮
        </button>
        {menuOpen === row.id && (
          <div
            style={{
              position: 'absolute', right: 0, top: 28, width: 160, zIndex: 50,
              background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4,
            }}
            onClick={e => e.stopPropagation()}
          >
            {[
              { label: lang === 'es' ? 'Editar' : 'Edit', icon: '✏️', action: () => { onSelectWorkflow(row.id); setMenuOpen(null) } },
              { label: lang === 'es' ? 'Renombrar' : 'Rename', icon: '📝', action: () => { setRenaming(row.id); setRenameValue(row.name); setMenuOpen(null) } },
              { label: lang === 'es' ? 'Eliminar' : 'Delete', icon: '🗑️', action: () => handleDelete(row), color: '#EF4444' },
            ].map((item, i) => (
              <div
                key={i}
                onClick={item.action}
                style={{
                  padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
                  display: 'flex', alignItems: 'center', gap: 8,
                  color: item.color || '#374151', transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#F9FAFB'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{ fontSize: 14 }}>{item.icon}</span>
                {item.label}
              </div>
            ))}
          </div>
        )}
      </div>
    )},
  ]

  // Merge API workflows (real) + demo workflows (fallback)
  let realWorkflows = []
  try {
    realWorkflows = (apiWorkflows || []).map(w => ({
      id: w?.id || Math.random().toString(),
      name: w?.name || 'Unnamed',
      status: w?.status || 'active',
      version: 'v' + (w?.version || '1.0'),
      steps: w?.dag_definition?.steps?.length || w?.steps_count || 0,
      created: w?.created_at?.slice(0, 10) || 'now',
    }))
  } catch { realWorkflows = [] }
  const workflows = [...realWorkflows, ...DEMO_WORKFLOWS]
  const filtered = filter === 'all' ? workflows : workflows.filter((w) => w.status === filter)

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 24, flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827' }}>
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
              borderColor: filter === f.key ? 'rgba(99,102,241,0.4)' : '#E5E7EB',
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
      {filtered.length === 0 ? (
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
        <div data-tour="workflow-table" style={{
          background: '#FFFFFF', borderRadius: 12,
          border: '1px solid #E5E7EB', overflow: 'hidden',
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
        onCreated={(wf) => { if (wf) setLocalWorkflows(prev => [wf, ...prev]); setShowCreate(false) }}
      />
    </div>
  )
}
