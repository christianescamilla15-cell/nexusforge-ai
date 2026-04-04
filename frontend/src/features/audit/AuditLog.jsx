import { useState, useEffect, useCallback } from 'react'
import { fetchAPI, getApiUrl } from '../../services/api'

const ACTION_COLORS = {
  created: '#10B981',
  updated: '#3B82F6',
  deleted: '#EF4444',
  executed: '#8B5CF6',
  published: '#F59E0B',
}

const ENTITY_TYPES = ['automation', 'workflow', 'agent_config', 'connector', 'rule', 'variable']

const T = {
  en: {
    title: 'Audit Log',
    timestamp: 'Timestamp',
    user: 'User',
    entity: 'Entity',
    action: 'Action',
    changes: 'Changes',
    export: 'Export CSV',
    empty: 'No audit entries found.',
    allTypes: 'All types',
    prev: 'Previous',
    next: 'Next',
    page: 'Page',
  },
  es: {
    title: 'Registro de Auditoría',
    timestamp: 'Fecha',
    user: 'Usuario',
    entity: 'Entidad',
    action: 'Acción',
    changes: 'Cambios',
    export: 'Exportar CSV',
    empty: 'Sin entradas de auditoría.',
    allTypes: 'Todos los tipos',
    prev: 'Anterior',
    next: 'Siguiente',
    page: 'Página',
  },
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function ChangesCell({ changes }) {
  if (!changes || Object.keys(changes).length === 0) {
    return <span style={{ color: '#D1D5DB' }}>--</span>
  }
  return (
    <div style={{ fontSize: 11, lineHeight: 1.5, maxWidth: 280 }}>
      {Object.entries(changes).map(([key, val]) => {
        if (val && typeof val === 'object' && 'old' in val && 'new' in val) {
          return (
            <div key={key} style={{ marginBottom: 2 }}>
              <span style={{ fontWeight: 600, color: '#6B7280' }}>{key}: </span>
              <span style={{ color: '#EF4444', textDecoration: 'line-through' }}>
                {String(val.old ?? '')}
              </span>
              <span style={{ color: '#9CA3AF' }}> → </span>
              <span style={{ color: '#10B981' }}>{String(val.new ?? '')}</span>
            </div>
          )
        }
        return (
          <div key={key} style={{ marginBottom: 2 }}>
            <span style={{ fontWeight: 600, color: '#6B7280' }}>{key}: </span>
            <span style={{ color: '#374151' }}>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function AuditLog({ entityType, entityId, lang = 'en' }) {
  const t = T[lang] || T.en
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [filterType, setFilterType] = useState(entityType || '')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const limit = 20

  const load = useCallback(async () => {
    setLoading(true)
    let url
    if (entityType && entityId) {
      url = `/audit/entity/${entityType}/${entityId}?limit=${limit}&offset=${page * limit}`
    } else {
      const typeParam = filterType ? `&entity_type=${filterType}` : ''
      const fromParam = dateFrom ? `&from=${dateFrom}` : ''
      const toParam = dateTo ? `&to=${dateTo}` : ''
      url = `/audit/?limit=${limit}&offset=${page * limit}${typeParam}${fromParam}${toParam}`
    }
    const res = await fetchAPI(url)
    if (res.data) {
      setItems(res.data.items || [])
      setTotal(res.data.total || 0)
    }
    setLoading(false)
  }, [entityType, entityId, filterType, dateFrom, dateTo, page])

  useEffect(() => { load() }, [load])

  const handleExport = () => {
    const apiUrl = getApiUrl()
    const token = typeof window !== 'undefined' ? localStorage.getItem('nf_token') : ''
    const typeParam = filterType ? `?entity_type=${filterType}` : ''
    // Open in new tab with auth header via fetch+blob
    fetch(`${apiUrl}/audit/export${typeParam}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'audit_logs.csv'
        a.click()
        URL.revokeObjectURL(url)
      })
      .catch(() => {})
  }

  const totalPages = Math.ceil(total / limit)

  // ── Styles ──
  const card = { background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', overflow: 'hidden' }
  const header = {
    padding: '14px 20px', borderBottom: '1px solid #F3F4F6',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10,
  }
  const thStyle = {
    padding: '10px 14px', textAlign: 'left', fontSize: 11,
    fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase',
  }
  const tdStyle = { padding: '10px 14px', fontSize: 13, color: '#374151', verticalAlign: 'top' }
  const selectStyle = {
    padding: '5px 10px', borderRadius: 6, border: '1px solid #D1D5DB',
    fontSize: 12, color: '#374151', outline: 'none', background: '#fff',
  }

  return (
    <div style={card}>
      <div style={header}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
          {t.title}
        </h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {!entityType && (
            <>
              <select
                style={selectStyle}
                value={filterType}
                onChange={e => { setFilterType(e.target.value); setPage(0) }}
              >
                <option value="">{t.allTypes}</option>
                {ENTITY_TYPES.map(et => (
                  <option key={et} value={et}>{et}</option>
                ))}
              </select>
              <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(0) }}
                style={selectStyle} title={lang === 'es' ? 'Desde' : 'From'} />
              <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(0) }}
                style={selectStyle} title={lang === 'es' ? 'Hasta' : 'To'} />
            </>
          )}
          <button
            onClick={handleExport}
            style={{
              padding: '6px 14px', borderRadius: 8, border: '1px solid #E5E7EB',
              background: '#fff', color: '#374151', fontSize: 12,
              fontWeight: 600, cursor: 'pointer',
            }}
          >
            {t.export}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>...</div>
      ) : items.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
          {t.empty}
        </div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
                  <th style={thStyle}>{t.timestamp}</th>
                  <th style={thStyle}>{t.user}</th>
                  <th style={thStyle}>{t.entity}</th>
                  <th style={thStyle}>{t.action}</th>
                  <th style={thStyle}>{t.changes}</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={{ ...tdStyle, whiteSpace: 'nowrap', fontSize: 12, color: '#6B7280' }}>
                      {formatDate(item.created_at, lang)}
                    </td>
                    <td style={{ ...tdStyle, fontSize: 12 }}>
                      {item.user_id ? item.user_id.slice(0, 8) + '...' : 'system'}
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 4,
                        background: '#F3F4F6', fontSize: 11, fontWeight: 500, color: '#6B7280',
                      }}>
                        {item.entity_type}
                      </span>
                      <span style={{ fontSize: 10, color: '#9CA3AF', marginLeft: 4, fontFamily: 'monospace' }}>
                        {item.entity_id?.slice(0, 8)}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        display: 'inline-block', padding: '2px 10px', borderRadius: 9999,
                        fontSize: 11, fontWeight: 600,
                        color: ACTION_COLORS[item.action] || '#6B7280',
                        background: `${ACTION_COLORS[item.action] || '#6B7280'}15`,
                      }}>
                        {item.action}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <ChangesCell changes={item.changes} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              padding: '12px 20px', borderTop: '1px solid #F3F4F6',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              fontSize: 12, color: '#6B7280',
            }}>
              <span>{t.page} {page + 1} / {totalPages} ({total} total)</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  disabled={page === 0}
                  onClick={() => setPage(p => p - 1)}
                  style={{
                    padding: '4px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                    background: page === 0 ? '#F9FAFB' : '#fff', cursor: page === 0 ? 'default' : 'pointer',
                    fontSize: 12, color: page === 0 ? '#D1D5DB' : '#374151',
                  }}
                >
                  {t.prev}
                </button>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage(p => p + 1)}
                  style={{
                    padding: '4px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                    background: page >= totalPages - 1 ? '#F9FAFB' : '#fff',
                    cursor: page >= totalPages - 1 ? 'default' : 'pointer',
                    fontSize: 12, color: page >= totalPages - 1 ? '#D1D5DB' : '#374151',
                  }}
                >
                  {t.next}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
