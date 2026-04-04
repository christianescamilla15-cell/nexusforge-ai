import { useState, useEffect } from 'react'

const PAGE_SIZE = 20

export default function ResultsTable({
  results = [],
  columns = [],
  lang,
  onRowClick,
  renderCell,
  emptyIcon = '📋',
  emptyTitle,
  emptyDescription,
}) {
  const [page, setPage] = useState(0)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const totalPages = Math.ceil(results.length / PAGE_SIZE)
  const paged = results.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  if (results.length === 0) {
    return (
      <div style={{
        padding: '48px 24px',
        textAlign: 'center',
        background: '#fff',
        borderRadius: 12,
        border: '1px solid #E5E7EB',
      }}>
        <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>{emptyIcon}</div>
        <h4 style={{ fontSize: 15, fontWeight: 600, color: '#374151', margin: '0 0 6px' }}>
          {emptyTitle || (lang === 'es' ? 'Sin resultados aun' : 'No results yet')}
        </h4>
        <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>
          {emptyDescription || (lang === 'es'
            ? 'Procesa tu primer elemento para ver resultados aqui.'
            : 'Process your first item to see results here.')}
        </p>
      </div>
    )
  }

  // Mobile: card layout
  if (isMobile) {
    return (
      <div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {paged.map((row, ri) => (
            <div
              key={row.id || ri}
              onClick={() => onRowClick && onRowClick(row)}
              style={{
                background: '#fff',
                borderRadius: 10,
                border: '1px solid #E5E7EB',
                padding: 14,
                cursor: onRowClick ? 'pointer' : 'default',
                transition: 'border-color 0.15s',
              }}
              onMouseEnter={e => onRowClick && (e.currentTarget.style.borderColor = '#6366F1')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#E5E7EB')}
            >
              {columns.map((col, ci) => (
                <div key={ci} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '3px 0',
                  fontSize: 13,
                }}>
                  <span style={{ color: '#9CA3AF', fontWeight: 500 }}>{col.label}</span>
                  <span style={{ color: '#374151' }}>
                    {renderCell ? renderCell(row, col.key, ci) : (row[col.key] ?? '--')}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
        {totalPages > 1 && <Pagination page={page} totalPages={totalPages} onPage={setPage} />}
      </div>
    )
  }

  // Desktop: table layout
  return (
    <div>
      <div style={{
        background: '#fff',
        borderRadius: 12,
        border: '1px solid #E5E7EB',
        overflow: 'hidden',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
              {columns.map((col, i) => (
                <th key={i} style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#9CA3AF',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                  whiteSpace: 'nowrap',
                }}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, ri) => (
              <tr
                key={row.id || ri}
                onClick={() => onRowClick && onRowClick(row)}
                style={{
                  borderBottom: '1px solid #F3F4F6',
                  cursor: onRowClick ? 'pointer' : 'default',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => onRowClick && (e.currentTarget.style.background = '#F9FAFB')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {columns.map((col, ci) => (
                  <td key={ci} style={{
                    padding: '10px 16px',
                    color: '#374151',
                    maxWidth: col.maxWidth || 'none',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: col.wrap ? 'normal' : 'nowrap',
                  }}>
                    {renderCell ? renderCell(row, col.key, ci) : (row[col.key] ?? '--')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && <Pagination page={page} totalPages={totalPages} onPage={setPage} />}
    </div>
  )
}

function Pagination({ page, totalPages, onPage }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 8,
      marginTop: 16,
    }}>
      <button
        onClick={() => onPage(Math.max(0, page - 1))}
        disabled={page === 0}
        style={{
          padding: '6px 12px',
          borderRadius: 6,
          border: '1px solid #E5E7EB',
          background: page === 0 ? '#F9FAFB' : '#fff',
          color: page === 0 ? '#D1D5DB' : '#374151',
          fontSize: 12,
          cursor: page === 0 ? 'default' : 'pointer',
        }}
      >
        ←
      </button>
      <span style={{ fontSize: 12, color: '#6B7280' }}>
        {page + 1} / {totalPages}
      </span>
      <button
        onClick={() => onPage(Math.min(totalPages - 1, page + 1))}
        disabled={page >= totalPages - 1}
        style={{
          padding: '6px 12px',
          borderRadius: 6,
          border: '1px solid #E5E7EB',
          background: page >= totalPages - 1 ? '#F9FAFB' : '#fff',
          color: page >= totalPages - 1 ? '#D1D5DB' : '#374151',
          fontSize: 12,
          cursor: page >= totalPages - 1 ? 'default' : 'pointer',
        }}
      >
        →
      </button>
    </div>
  )
}
