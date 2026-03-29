import DataTable from '../../shared/components/DataTable'
import StatusBadge from '../../shared/components/StatusBadge'

const columns = [
  { key: 'status', label: 'Estado', render: (v) => <StatusBadge status={v} /> },
  { key: 'workflow_name', label: 'Flujo de Trabajo' },
  { key: 'id', label: 'ID Ejecucion', render: (v) => typeof v === 'string' ? v.slice(0, 8) : v },
  { key: 'total_latency_ms', label: 'Latencia', render: (v) => v ? `${v}ms` : '--' },
]

export default function RecentRuns({ runs }) {
  return (
    <div style={{
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB', overflow: 'hidden',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #E5E7EB',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>Ejecuciones Recientes</h3>
        <span style={{ fontSize: 12, color: '#9CA3AF' }}>{runs.length} resultados</span>
      </div>
      {runs.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
          No hay ejecuciones registradas
        </div>
      ) : (
        <DataTable columns={columns} data={runs} />
      )}
    </div>
  )
}
