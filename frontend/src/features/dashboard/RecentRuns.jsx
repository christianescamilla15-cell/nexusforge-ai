import DataTable from '../../shared/components/DataTable'
import StatusBadge from '../../shared/components/StatusBadge'

const columns = [
  { key: 'status', label: 'Estado', render: (v) => <StatusBadge status={v} /> },
  { key: 'workflow', label: 'Workflow' },
  { key: 'started', label: 'Inicio' },
  { key: 'duration', label: 'Duracion' },
  { key: 'cost', label: 'Costo', render: (v) => `$${v}` },
  { key: 'steps', label: 'Pasos' },
]

export default function RecentRuns({ runs }) {
  return (
    <div style={{
      background: '#161E2E', borderRadius: 12,
      border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
    }}>
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>Ejecuciones Recientes</h3>
        <span style={{ fontSize: 12, color: '#9CA3AF' }}>{runs.length} resultados</span>
      </div>
      <DataTable columns={columns} data={runs} />
    </div>
  )
}
