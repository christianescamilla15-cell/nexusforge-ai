import { useState, useEffect } from 'react'
import { t } from '../../shared/i18n/translations'
import { fetchAPI } from '../../services/api'
import StatusBadge from '../../shared/components/StatusBadge'
import Skeleton from '../../shared/components/Skeleton'
import { timeAgo } from '../../shared/utils/timeAgo'
import CostTokenDashboard from '../metrics/CostTokenDashboard'
import ConfirmModal from '../../shared/components/ConfirmModal'
import { useConfirm } from '../../shared/hooks/useConfirm'

function formatDuration(ms) {
  if (!ms && ms !== 0) return '--'
  if (ms < 1000) return `${ms}ms`
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  const d = new Date(iso)
  const locale = lang === 'es' ? 'es-ES' : 'en-US'
  return d.toLocaleString(locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function ExecutionListPage({ onSelectExecution, lang = 'en' }) {
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [isMobile, setIsMobile] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [menuOpen, setMenuOpen] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [activeTab, setActiveTab] = useState('executions')
  const [confirmState, showConfirm] = useConfirm()

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const loadExecutions = () => {
    setLoading(true)
    fetchAPI('/executions/').then((res) => {
      if (res.error) {
        setError(res.error)
      } else {
        const raw = Array.isArray(res.data) ? res.data : (res.data?.runs || [])
        const runs = raw.map((r) => ({
          run_id: r.id || r.run_id,
          workflow_name: r.workflow_name || 'Workflow',
          status: r.status,
          started_at: r.started_at || r.created_at,
          duration_ms: r.total_latency_ms || r.latency_ms
            || (r.completed_at && r.started_at ? new Date(r.completed_at) - new Date(r.started_at) : null),
          total_cost: r.total_cost_usd || r.total_cost || r.cost || 0,
          steps_count: r.steps_count || r.steps?.length || r.agents_used?.length || 0,
        }))
        setExecutions(runs)
      }
      setLoading(false)
    })
  }

  useEffect(() => { loadExecutions() }, [])

  // Auto-refresh: always poll every 10s for the first 60s after mount,
  // then only continue if there are active runs.
  useEffect(() => {
    const mountTime = Date.now()
    const interval = setInterval(() => {
      const elapsed = Date.now() - mountTime
      const hasActive = executions.some(e => e.status === 'running' || e.status === 'pending')
      if (elapsed < 60_000 || hasActive) {
        loadExecutions()
      } else {
        clearInterval(interval)
      }
    }, 10_000)
    return () => clearInterval(interval)
  }, [executions])

  // Refresh when the tab regains focus (e.g. navigating back from WorkflowDetailPage)
  useEffect(() => {
    const onFocus = () => loadExecutions()
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [])

  const FILTERS = [
    { key: 'all', label: t('all', lang) },
    { key: 'pending', label: t('pending', lang) },
    { key: 'running', label: t('running', lang) },
    { key: 'completed', label: t('completed', lang) },
    { key: 'failed', label: t('failed', lang) },
    { key: 'cancelled', label: lang === 'es' ? 'Cancelado' : 'Cancelled' },
  ]

  const filtered = filter === 'all' ? executions : executions.filter((e) => e.status === filter)

  const toggleSelect = (id, e) => {
    e.stopPropagation()
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filtered.map(e => e.run_id)))
    }
  }

  const handleDelete = async (runId) => {
    const ok = await showConfirm(lang === 'es' ? `¿Eliminar esta ejecución?` : `Delete this execution?`)
    if (!ok) return
    setDeleting(true)
    const res = await fetchAPI(`/executions/${runId}`, { method: 'DELETE' })
    if (res.error) {
      setError(res.error)
      setDeleting(false)
      setMenuOpen(null)
      return
    }
    setExecutions(prev => prev.filter(e => e.run_id !== runId))
    setMenuOpen(null)
    setDeleting(false)
  }

  const handleDeleteSelected = async () => {
    if (selected.size === 0) return
    const msg = lang === 'es'
      ? `¿Eliminar ${selected.size} ejecuciones seleccionadas?`
      : `Delete ${selected.size} selected executions?`
    const ok = await showConfirm(msg)
    if (!ok) return
    setDeleting(true)
    const results = await Promise.all([...selected].map(id =>
      fetchAPI(`/executions/${id}`, { method: 'DELETE' })
    ))
    const firstError = results.find(r => r.error)
    if (firstError) {
      setError(firstError.error)
    }
    setExecutions(prev => prev.filter(e => !selected.has(e.run_id)))
    setSelected(new Set())
    setDeleting(false)
  }

  const handleRerun = async (exec) => {
    setMenuOpen(null)
    // Find the workflow_id from the original execution
    const res = await fetchAPI(`/executions/${exec.run_id}`)
    if (res.error) {
      setError(res.error)
      return
    }
    if (res.data?.workflow_id) {
      const runRes = await fetchAPI('/executions/', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: res.data.workflow_id,
          trigger_type: 'manual',
          input_data: {},
        }),
      })
      if (runRes.error) {
        setError(runRes.error)
        return
      }
      loadExecutions()
    }
  }

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [menuOpen])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
            {t('executions', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {t('monitorExecutions', lang)}
            <span style={{ marginLeft: 8, color: '#6366F1' }}>{executions.length} {t('total', lang)}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {/* Bulk delete button */}
          {selected.size > 0 && (
            <button
              onClick={handleDeleteSelected}
              disabled={deleting}
              style={{
                padding: '8px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600,
                background: 'rgba(239,68,68,0.1)', color: '#DC2626', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
                opacity: deleting ? 0.5 : 1,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
              </svg>
              {lang === 'es' ? `Eliminar (${selected.size})` : `Delete (${selected.size})`}
            </button>
          )}
          {/* Refresh button */}
          <button
            onClick={loadExecutions}
            style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB', fontSize: 13,
              fontWeight: 500, background: '#fff', color: '#6B7280', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {lang === 'es' ? 'Actualizar' : 'Refresh'}
          </button>
        </div>
      </div>

      {loading && <Skeleton.Table rows={6} />}

      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 20,
          background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
          color: '#991B1B', fontSize: 14,
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E5E7EB' }}>
        {[
          { key: 'executions', label: lang === 'es' ? 'Ejecuciones' : 'Executions', icon: '⚡' },
          { key: 'metrics', label: lang === 'es' ? 'Métricas' : 'Metrics', icon: '📊' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 20px', border: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: 600, background: 'none',
              color: activeTab === tab.key ? '#6366F1' : '#9CA3AF',
              borderBottom: activeTab === tab.key ? '2px solid #6366F1' : '2px solid transparent',
              marginBottom: -2, display: 'flex', alignItems: 'center', gap: 6,
              transition: 'all 0.15s',
            }}
          >
            <span style={{ fontSize: 16 }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Metrics Tab */}
      {activeTab === 'metrics' && <CostTokenDashboard lang={lang} embedded />}

      {/* Executions Tab */}
      {activeTab === 'executions' && <>
      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '6px 14px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 500,
              cursor: 'pointer', transition: 'all 0.15s',
              background: filter === f.key ? 'rgba(99,102,241,0.2)' : '#F3F4F6',
              color: filter === f.key ? '#818CF8' : '#9CA3AF',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {!loading && <div data-tour="execution-table" style={{
        background: '#FFFFFF', borderRadius: 12, border: '1px solid #E5E7EB',
        overflow: 'hidden', overflowX: 'auto',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? 600 : undefined }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
              <th style={{ padding: '12px 8px 12px 16px', width: 40 }}>
                <input
                  type="checkbox"
                  checked={filtered.length > 0 && selected.size === filtered.length}
                  onChange={toggleSelectAll}
                  style={{ cursor: 'pointer', accentColor: '#6366F1' }}
                />
              </th>
              {[
                t('status', lang),
                t('workflow', lang),
                t('start', lang),
                t('duration', lang),
                t('cost', lang),
                t('steps', lang),
                '',
              ].map((h, i) => (
                <th key={i} style={{
                  padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                  {t('noExecutionsFilter', lang)}
                </td>
              </tr>
            )}
            {filtered.map((exec) => (
              <tr
                key={exec.run_id}
                onClick={() => onSelectExecution && onSelectExecution(exec.run_id)}
                style={{
                  borderBottom: '1px solid #F3F4F6',
                  cursor: 'pointer', transition: 'background 0.15s',
                  background: selected.has(exec.run_id) ? 'rgba(99,102,241,0.04)' : 'transparent',
                }}
                onMouseEnter={(e) => { if (!selected.has(exec.run_id)) e.currentTarget.style.background = '#F9FAFB' }}
                onMouseLeave={(e) => { if (!selected.has(exec.run_id)) e.currentTarget.style.background = 'transparent' }}
              >
                <td style={{ padding: '12px 8px 12px 16px', width: 40 }} onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selected.has(exec.run_id)}
                    onChange={(e) => toggleSelect(exec.run_id, e)}
                    style={{ cursor: 'pointer', accentColor: '#6366F1' }}
                  />
                </td>
                <td style={{ padding: '12px 16px' }}><StatusBadge status={exec.status} /></td>
                <td style={{ padding: '12px 16px', color: '#111827', fontSize: 14, fontWeight: 500 }}>{exec.workflow_name}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13, whiteSpace: 'nowrap' }} title={formatDate(exec.started_at, lang)}>{timeAgo(exec.started_at, lang)}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{formatDuration(exec.duration_ms)}</td>
                <td style={{ padding: '12px 16px', color: '#10B981', fontSize: 13, fontWeight: 500 }}>${Number(exec.total_cost || 0) > 0 ? Number(exec.total_cost || 0).toFixed(5) : '0.00'}</td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>{exec.steps_count}</td>
                <td style={{ padding: '12px 8px', position: 'relative' }} onClick={e => e.stopPropagation()}>
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === exec.run_id ? null : exec.run_id) }}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px',
                      fontSize: 18, color: '#9CA3AF', borderRadius: 6,
                    }}
                  >
                    ⋮
                  </button>
                  {menuOpen === exec.run_id && (
                    <div
                      style={{
                        position: 'absolute', right: 8, top: 36, width: 180, zIndex: 50,
                        background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10,
                        boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4,
                      }}
                      onClick={e => e.stopPropagation()}
                    >
                      {[
                        {
                          label: lang === 'es' ? 'Ver detalle' : 'View details',
                          icon: '👁️',
                          action: () => { onSelectExecution && onSelectExecution(exec.run_id); setMenuOpen(null) },
                        },
                        ...(exec.status === 'completed' || exec.status === 'failed' ? [{
                          label: lang === 'es' ? 'Re-ejecutar' : 'Re-run',
                          icon: '🔄',
                          action: () => handleRerun(exec),
                        }] : []),
                        ...(exec.status === 'running' || exec.status === 'pending' ? [{
                          label: lang === 'es' ? 'Cancelar' : 'Cancel',
                          icon: '⏹️',
                          action: async () => {
                            await fetchAPI(`/executions/${exec.run_id}`, { method: 'DELETE' })
                            setExecutions(prev => prev.map(e => e.run_id === exec.run_id ? { ...e, status: 'cancelled' } : e))
                            setMenuOpen(null)
                          },
                          color: '#F59E0B',
                        }] : []),
                        {
                          label: lang === 'es' ? 'Eliminar' : 'Delete',
                          icon: '🗑️',
                          action: () => handleDelete(exec.run_id),
                          color: '#EF4444',
                        },
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>}
      </>}
      {confirmState && <ConfirmModal {...confirmState} />}
    </div>
  )
}
