import { useState } from 'react'
import SwarmCard from './SwarmCard'
import SwarmExecuteModal from './SwarmExecuteModal'

const TOPOLOGIES = ['sequential', 'parallel', 'hierarchical', 'debate', 'consensus', 'adaptive']

export default function SwarmListPage() {
  const [executing, setExecuting] = useState(null)

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 4 }}>Swarm Topologies</h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          Orquesta multiples agentes con diferentes patrones de ejecucion.
          <span style={{ marginLeft: 8, color: '#6366F1' }}>{TOPOLOGIES.length} topologias</span>
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
      }}>
        {TOPOLOGIES.map((t) => (
          <SwarmCard key={t} topology={t} onExecute={(top) => setExecuting(top)} />
        ))}
      </div>

      {executing && (
        <SwarmExecuteModal topology={executing} onClose={() => setExecuting(null)} />
      )}
    </div>
  )
}
