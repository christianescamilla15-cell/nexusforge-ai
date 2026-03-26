import { useState, useMemo } from 'react'

const cellStyle = {
  padding: '12px 16px', fontSize: 13, borderBottom: '1px solid rgba(255,255,255,0.04)',
  textAlign: 'left', whiteSpace: 'nowrap',
}

const headerStyle = {
  ...cellStyle,
  color: '#9CA3AF', fontWeight: 500, fontSize: 12, textTransform: 'uppercase',
  letterSpacing: '0.05em', cursor: 'pointer', userSelect: 'none',
  background: 'rgba(255,255,255,0.02)',
}

export default function DataTable({ columns, data = [], pageSize = 0, onRowClick }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)

  const handleSort = (key) => {
    if (sortCol === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    if (!sortCol) return data
    return [...data].sort((a, b) => {
      const va = a[sortCol], vb = b[sortCol]
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [data, sortCol, sortDir])

  const paginated = pageSize > 0
    ? sorted.slice(page * pageSize, (page + 1) * pageSize)
    : sorted

  const totalPages = pageSize > 0 ? Math.ceil(data.length / pageSize) : 1

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => col.sortable !== false && handleSort(col.key)}
                aria-label={`Ordenar por ${col.label}`}
                style={{
                  ...headerStyle,
                  cursor: col.sortable !== false ? 'pointer' : 'default',
                }}
              >
                {col.label}
                {sortCol === col.key && (
                  <span style={{ marginLeft: 4 }}>{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {paginated.map((row, i) => (
            <tr
              key={row.id || i}
              onClick={() => onRowClick && onRowClick(row)}
              style={{
                cursor: onRowClick ? 'pointer' : 'default',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(99,102,241,0.05)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              {columns.map((col) => (
                <td key={col.key} style={cellStyle}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {pageSize > 0 && totalPages > 1 && (
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
          gap: 8, padding: '12px 16px', fontSize: 13, color: '#9CA3AF',
        }}>
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            aria-label="Pagina anterior"
            style={{
              padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
              background: 'transparent', color: '#E5E7EB', fontSize: 13,
              opacity: page === 0 ? 0.3 : 1,
            }}
          >
            Anterior
          </button>
          <span>{page + 1} / {totalPages}</span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            aria-label="Pagina siguiente"
            style={{
              padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
              background: 'transparent', color: '#E5E7EB', fontSize: 13,
              opacity: page >= totalPages - 1 ? 0.3 : 1,
            }}
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  )
}
