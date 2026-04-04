import { useState } from 'react'

/**
 * AutoDashboardGenerator — analyzes output_data shape and renders
 * appropriate widgets (KPI, badge, table, tags, panel, text) automatically.
 * No manual configuration needed: any automation output gets a reasonable dashboard.
 */

function humanize(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, c => c.toUpperCase())
}

function analyzeOutputSchema(outputData) {
  if (!outputData || typeof outputData !== 'object') return []
  const widgets = []

  for (const [key, value] of Object.entries(outputData)) {
    if (typeof value === 'number') {
      widgets.push({ type: 'kpi', field: key, label: humanize(key) })
    } else if (typeof value === 'boolean') {
      widgets.push({ type: 'badge', field: key, label: humanize(key) })
    } else if (Array.isArray(value)) {
      if (value.length > 0 && typeof value[0] === 'object') {
        widgets.push({ type: 'table', field: key, label: humanize(key), columns: Object.keys(value[0]) })
      } else {
        widgets.push({ type: 'tags', field: key, label: humanize(key) })
      }
    } else if (typeof value === 'string' && value.length > 200) {
      widgets.push({ type: 'panel', field: key, label: humanize(key) })
    } else if (typeof value === 'string') {
      widgets.push({ type: 'text', field: key, label: humanize(key) })
    } else if (typeof value === 'object' && value !== null) {
      widgets.push({ type: 'panel', field: key, label: humanize(key) })
    }
  }
  return widgets
}

/* ── Individual widget renderers ───────────────────────────────────────── */

function KPIWidget({ label, value }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '16px 20px', textAlign: 'center', minWidth: 120,
    }}>
      <p style={{ fontSize: 11, fontWeight: 600, color: '#9CA3AF', margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </p>
      <p style={{ fontSize: 28, fontWeight: 700, color: '#111827', margin: 0 }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
    </div>
  )
}

function BadgeWidget({ label, value }) {
  const isTrue = Boolean(value)
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <span style={{ fontSize: 12, fontWeight: 600, color: '#6B7280' }}>{label}</span>
      <span style={{
        padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
        background: isTrue ? '#D1FAE5' : '#FEE2E2',
        color: isTrue ? '#059669' : '#DC2626',
      }}>
        {isTrue ? 'True' : 'False'}
      </span>
    </div>
  )
}

function TableWidget({ label, data, columns }) {
  if (!Array.isArray(data) || data.length === 0) return null
  const cols = columns || Object.keys(data[0] || {})
  const displayRows = data.slice(0, 20)

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: 16, overflow: 'hidden',
    }}>
      <p style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', margin: '0 0 10px', textTransform: 'uppercase' }}>
        {label} ({data.length})
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {cols.map(col => (
                <th key={col} style={{
                  textAlign: 'left', padding: '8px 10px', borderBottom: '2px solid #E5E7EB',
                  fontWeight: 600, color: '#374151', whiteSpace: 'nowrap',
                }}>
                  {humanize(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i}>
                {cols.map(col => (
                  <td key={col} style={{
                    padding: '7px 10px', borderBottom: '1px solid #F3F4F6',
                    color: '#6B7280', maxWidth: 200, overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {typeof row[col] === 'object' ? JSON.stringify(row[col]) : String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > 20 && (
        <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 8, textAlign: 'center' }}>
          +{data.length - 20} more rows
        </p>
      )}
    </div>
  )
}

function TagsWidget({ label, data }) {
  if (!Array.isArray(data)) return null
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: 16,
    }}>
      <p style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', margin: '0 0 10px', textTransform: 'uppercase' }}>
        {label}
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {data.slice(0, 30).map((item, i) => (
          <span key={i} style={{
            padding: '3px 10px', borderRadius: 6, fontSize: 11,
            background: '#EEF2FF', color: '#4338CA', fontWeight: 500,
          }}>
            {String(item)}
          </span>
        ))}
        {data.length > 30 && (
          <span style={{ fontSize: 11, color: '#9CA3AF', alignSelf: 'center' }}>
            +{data.length - 30} more
          </span>
        )}
      </div>
    </div>
  )
}

function PanelWidget({ label, data }) {
  const [expanded, setExpanded] = useState(false)
  const str = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  const isLong = str.length > 300

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', margin: 0, textTransform: 'uppercase' }}>
          {label}
        </p>
        {isLong && (
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              background: 'none', border: 'none', fontSize: 11,
              color: '#6366F1', cursor: 'pointer', fontWeight: 500, padding: 0,
            }}
          >
            {expanded ? '\u25B2 Collapse' : '\u25BC Expand'}
          </button>
        )}
      </div>
      <div style={{
        padding: 12, background: '#F9FAFB', borderRadius: 8,
        border: '1px solid #E5E7EB', fontSize: 12, fontFamily: 'monospace',
        color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        maxHeight: expanded ? 'none' : 200, overflow: 'hidden',
      }}>
        {expanded || !isLong ? str : str.slice(0, 300) + '...'}
      </div>
    </div>
  )
}

function TextWidget({ label, value }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
      padding: '14px 20px',
    }}>
      <p style={{ fontSize: 11, fontWeight: 600, color: '#9CA3AF', margin: '0 0 4px', textTransform: 'uppercase' }}>
        {label}
      </p>
      <p style={{ fontSize: 14, color: '#111827', margin: 0, lineHeight: 1.5 }}>
        {value}
      </p>
    </div>
  )
}

/* ── Main component ────────────────────────────────────────────────────── */

export default function AutoDashboardGenerator({ outputData, lang }) {
  if (!outputData || typeof outputData !== 'object' || Object.keys(outputData).length === 0) {
    return (
      <div style={{
        padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13,
        background: '#F9FAFB', borderRadius: 12, border: '1px solid #E5E7EB',
      }}>
        {lang === 'es' ? 'Sin datos para visualizar' : 'No data to visualize'}
      </div>
    )
  }

  const widgets = analyzeOutputSchema(outputData)

  // Separate KPI/badge widgets (inline row) from larger widgets (full width)
  const inlineWidgets = widgets.filter(w => w.type === 'kpi' || w.type === 'badge' || w.type === 'text')
  const fullWidgets = widgets.filter(w => w.type === 'table' || w.type === 'tags' || w.type === 'panel')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* KPI / Badge / Text row */}
      {inlineWidgets.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fill, minmax(min(180px, 100%), 1fr))`,
          gap: 12,
        }}>
          {inlineWidgets.map(w => {
            const val = outputData[w.field]
            switch (w.type) {
              case 'kpi': return <KPIWidget key={w.field} label={w.label} value={val} />
              case 'badge': return <BadgeWidget key={w.field} label={w.label} value={val} />
              case 'text': return <TextWidget key={w.field} label={w.label} value={val} />
              default: return null
            }
          })}
        </div>
      )}

      {/* Full-width widgets */}
      {fullWidgets.map(w => {
        const val = outputData[w.field]
        switch (w.type) {
          case 'table': return <TableWidget key={w.field} label={w.label} data={val} columns={w.columns} />
          case 'tags': return <TagsWidget key={w.field} label={w.label} data={val} />
          case 'panel': return <PanelWidget key={w.field} label={w.label} data={val} />
          default: return null
        }
      })}
    </div>
  )
}

export { analyzeOutputSchema, humanize }
