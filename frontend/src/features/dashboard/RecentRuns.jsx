import { useState } from 'react'
import StatusBadge from '../../shared/components/StatusBadge'
import ConfirmModal from '../../shared/components/ConfirmModal'
import { useConfirm } from '../../shared/hooks/useConfirm'
import { fetchAPI } from '../../services/api'

const PAGE_SIZE = 10

export default function RecentRuns({ runs, lang = 'en', onClearAll }) {
  const [page, setPage] = useState(0)
  const [confirmState, showConfirm] = useConfirm()
  const [clearing, setClearing] = useState(false)

  const totalPages = Math.max(1, Math.ceil(runs.length / PAGE_SIZE))
  const paged = runs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleClearAll = async () => {
    const ok = await showConfirm(
      lang === 'es'
        ? `¿Eliminar las ${runs.length} ejecuciones recientes?`
        : `Clear all ${runs.length} recent executions?`,
      { confirmLabel: lang === 'es' ? 'Eliminar todo' : 'Clear all' }
    )
    if (!ok) return
    setClearing(true)
    if (onClearAll) await onClearAll()
    setClearing(false)
  }

  return (
    <div style={{
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB', overflow: 'hidden',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 20px', borderBottom: '1px solid #E5E7EB',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', margin: 0 }}>
          {lang === 'es' ? 'Ejecuciones Recientes' : 'Recent Executions'}
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, color: '#9CA3AF' }}>{runs.length} {lang === 'es' ? 'resultados' : 'results'}</span>
          {runs.length > 0 && (
            <button onClick={handleClearAll} disabled={clearing} style={{
              padding: '4px 10px', borderRadius: 6, border: '1px solid #FECACA',
              background: '#fff', fontSize: 11, color: '#EF4444', cursor: 'pointer', fontWeight: 600,
            }}>
              {clearing ? '...' : (lang === 'es' ? 'Limpiar' : 'Clear')}
            </button>
          )}
        </div>
      </div>

      {/* Table with fixed height + scroll */}
      {runs.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
          {lang === 'es' ? 'No hay ejecuciones registradas' : 'No executions recorded'}
        </div>
      ) : (
        <>
          <div style={{ maxHeight: 400, overflowY: 'auto', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 480 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB', position: 'sticky', top: 0, background: '#F9FAFB', zIndex: 1 }}>
                  <th style={thStyle}>{lang === 'es' ? 'Estado' : 'Status'}</th>
                  <th style={thStyle}>{lang === 'es' ? 'Flujo de Trabajo' : 'Workflow'}</th>
                  <th style={thStyle}>ID</th>
                  <th style={thStyle}>{lang === 'es' ? 'Latencia' : 'Latency'}</th>
                </tr>
              </thead>
              <tbody>
                {paged.map((run, i) => (
                  <tr key={run.id || i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={tdStyle}><StatusBadge status={run.status} /></td>
                    <td style={tdStyle}>{run.workflow_name || run.pipeline_name || '--'}</td>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12, color: '#9CA3AF' }}>
                      {typeof run.id === 'string' ? run.id.slice(0, 8) : run.id}
                    </td>
                    <td style={tdStyle}>{run.total_latency_ms || run.latency_ms ? `${run.total_latency_ms || run.latency_ms}ms` : '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              padding: '8px 16px', borderTop: '1px solid #F3F4F6',
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8,
            }}>
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                style={navBtn(page === 0)}>&larr;</button>
              <span style={{ fontSize: 12, color: '#6B7280' }}>{page + 1} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
                style={navBtn(page >= totalPages - 1)}>&rarr;</button>
            </div>
          )}
        </>
      )}

      {confirmState && <ConfirmModal {...confirmState} />}
    </div>
  )
}

const thStyle = {
  padding: '10px 16px', textAlign: 'left', fontSize: 11,
  fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase',
}
const tdStyle = { padding: '10px 16px', color: '#374151' }
const navBtn = (disabled) => ({
  padding: '4px 10px', borderRadius: 6, border: '1px solid #E5E7EB',
  background: '#fff', fontSize: 12, cursor: disabled ? 'default' : 'pointer',
  color: disabled ? '#D1D5DB' : '#374151',
})
