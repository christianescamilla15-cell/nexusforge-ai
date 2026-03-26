import { useState } from 'react'
import { useAPI } from '../../shared/hooks/useAPI'
import StatusBadge from '../../shared/components/StatusBadge'
import DataTable from '../../shared/components/DataTable'
import LoadingSpinner from '../../shared/components/LoadingSpinner'
import DAGVisualization from './DAGVisualization'
import { api } from '../../api/client'

const DEMO_WORKFLOW = {
  id: 'wf-1',
  name: 'Analisis de Documentos',
  description: 'Pipeline completo para ingerir, clasificar, resumir y validar documentos automaticamente con agentes IA.',
  status: 'active',
  version: 'v1.3',
  created_at: '2026-03-20T10:30:00Z',
  updated_at: '2026-03-25T14:15:00Z',
  dag_definition: {
    steps: [
      { name: 'ingest', type: 'extractor', depends_on: [] },
      { name: 'classify', type: 'classifier', depends_on: ['ingest'] },
      { name: 'summarize', type: 'summarizer', depends_on: ['classify'] },
      { name: 'validate', type: 'validator', depends_on: ['summarize'] },
    ],
  },
}

const DEMO_RUNS = [
  { id: 'run-1', status: 'completed', started: '2026-03-25 14:10', duration: '2m 14s', cost: '$0.23', steps_done: '4/4' },
  { id: 'run-2', status: 'completed', started: '2026-03-25 10:30', duration: '1m 58s', cost: '$0.19', steps_done: '4/4' },
  { id: 'run-3', status: 'failed', started: '2026-03-24 16:45', duration: '1m 02s', cost: '$0.11', steps_done: '2/4' },
  { id: 'run-4', status: 'completed', started: '2026-03-24 09:00', duration: '2m 30s', cost: '$0.25', steps_done: '4/4' },
]

const runColumns = [
  { key: 'status', label: 'Estado', render: (v) => <StatusBadge status={v} /> },
  { key: 'started', label: 'Inicio' },
  { key: 'duration', label: 'Duracion' },
  { key: 'cost', label: 'Costo' },
  { key: 'steps_done', label: 'Pasos' },
]

const statusMap = {
  active: 'completed',
  draft: 'pending',
  paused: 'cancelled',
  archived: 'pending',
}

export default function WorkflowDetailPage({ workflowId, onBack }) {
  const { data: workflow, loading, error } = useAPI(`/workflows/${workflowId}`)
  const { data: runs, loading: runsLoading } = useAPI(`/workflows/${workflowId}/runs`)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState(null)

  const wf = workflow || DEMO_WORKFLOW
  const runHistory = runs || DEMO_RUNS

  const handleRun = async () => {
    setRunning(true)
    setRunError(null)
    try {
      await api.post(`/workflows/${workflowId}/run`, {})
    } catch (e) {
      setRunError(e.message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button
          onClick={onBack}
          aria-label="Volver a la lista de workflows"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 36, height: 36, borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.08)', background: 'transparent',
            color: '#9CA3AF', cursor: 'pointer',
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M19 12H5m7-7l-7 7 7 7" />
          </svg>
        </button>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB' }}>{wf.name}</h1>
          <p style={{ fontSize: 14, color: '#9CA3AF', marginTop: 2 }}>{wf.description}</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onBack}
            aria-label="Editar workflow"
            style={{
              padding: '10px 18px', borderRadius: 8, fontSize: 14,
              border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
              color: '#E5E7EB', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            Editar
          </button>
          <button
            onClick={handleRun}
            disabled={running}
            aria-label="Ejecutar workflow"
            style={{
              padding: '10px 18px', borderRadius: 8, fontSize: 14, fontWeight: 500,
              border: 'none', background: '#6366F1', color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              opacity: running ? 0.6 : 1,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            {running ? 'Iniciando...' : 'Ejecutar'}
          </button>
        </div>
      </div>

      {runError && (
        <div style={{
          padding: '10px 16px', borderRadius: 8, marginBottom: 16, fontSize: 13,
          background: 'rgba(239,68,68,0.1)', color: '#EF4444',
          border: '1px solid rgba(239,68,68,0.2)',
        }}>
          Error al ejecutar: {runError}
        </div>
      )}

      {/* Info cards row */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        {[
          { label: 'Estado', value: <StatusBadge status={statusMap[wf.status] || wf.status} /> },
          { label: 'Version', value: wf.version },
          { label: 'Creado', value: new Date(wf.created_at).toLocaleDateString('es-ES') },
          { label: 'Actualizado', value: new Date(wf.updated_at).toLocaleDateString('es-ES') },
          { label: 'Pasos', value: wf.dag_definition?.steps?.length || 0 },
        ].map((info) => (
          <div key={info.label} style={{
            background: '#161E2E', borderRadius: 10, padding: '14px 18px',
            border: '1px solid rgba(255,255,255,0.06)', minWidth: 140,
          }}>
            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {info.label}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
              {info.value}
            </div>
          </div>
        ))}
      </div>

      {/* DAG Visualization */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', marginBottom: 24,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
            Grafo de Ejecucion (DAG)
          </h3>
        </div>
        <DAGVisualization steps={wf.dag_definition?.steps || []} />
      </div>

      {/* Run history */}
      <div style={{
        background: '#161E2E', borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>
            Historial de Ejecuciones
          </h3>
        </div>
        {runsLoading ? (
          <LoadingSpinner />
        ) : (
          <DataTable columns={runColumns} data={runHistory} pageSize={5} />
        )}
      </div>
    </div>
  )
}
