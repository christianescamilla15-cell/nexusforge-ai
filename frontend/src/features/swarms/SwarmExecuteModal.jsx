import { useState } from 'react'

const ALL_AGENTS = [
  'DocClassifier', 'EntityExtractor', 'SummaryAgent', 'ContentGen', 'FlowRouter',
  'DataValidator', 'SentimentAnalyzer', 'TranslationAgent', 'CodeReviewer', 'TestGenerator',
  'APIMapper', 'SchemaValidator', 'DataTransformer', 'ReportBuilder', 'AlertMonitor',
  'ComplianceChecker', 'PriorityRanker', 'DuplicateDetector', 'ContextLinker', 'AnomalyDetector',
  'FeedbackCollector', 'QualityAssurer',
]

export default function SwarmExecuteModal({ topology, onClose }) {
  const [selectedAgents, setSelectedAgents] = useState([])
  const [inputData, setInputData] = useState('{\n  "task": "Analizar documentos del Q4",\n  "documents": ["doc_1.pdf", "doc_2.pdf"]\n}')
  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState(null)

  const toggleAgent = (name) => {
    setSelectedAgents((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name]
    )
  }

  const handleExecute = () => {
    if (selectedAgents.length < 2) return
    setExecuting(true)
    setResult(null)
    setTimeout(() => {
      setResult({
        status: 'completed',
        topology,
        agents_used: selectedAgents.length,
        steps: selectedAgents.length * (topology === 'parallel' ? 1 : topology === 'debate' ? 3 : 2),
        duration: (Math.random() * 8 + 2).toFixed(1) + 's',
        output: `Swarm "${topology}" ejecutado con ${selectedAgents.length} agentes. Procesados ${Math.floor(Math.random() * 50 + 10)} items con 97.3% de exito.`,
      })
      setExecuting(false)
    }, 2200)
  }

  const topName = topology.charAt(0).toUpperCase() + topology.slice(1)

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 100, backdropFilter: 'blur(4px)',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#161E2E', borderRadius: 16, padding: 28,
          width: '90%', maxWidth: 620, maxHeight: '85vh', overflowY: 'auto',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#E5E7EB', margin: 0 }}>
              Ejecutar Swarm: {topName}
            </h2>
            <p style={{ fontSize: 13, color: '#9CA3AF', margin: '4px 0 0' }}>
              Selecciona agentes y configura la ejecucion
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            style={{
              background: 'rgba(255,255,255,0.06)', border: 'none', borderRadius: 8,
              width: 34, height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#9CA3AF', cursor: 'pointer', fontSize: 18,
            }}
          >
            x
          </button>
        </div>

        {/* Agent selection */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#E5E7EB', display: 'block', marginBottom: 8 }}>
            Agentes ({selectedAgents.length} seleccionados)
          </label>
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 6,
            maxHeight: 140, overflowY: 'auto', padding: 10,
            background: 'rgba(0,0,0,0.2)', borderRadius: 8,
          }}>
            {ALL_AGENTS.map((name) => {
              const sel = selectedAgents.includes(name)
              return (
                <button
                  key={name}
                  onClick={() => toggleAgent(name)}
                  aria-label={`${sel ? 'Deseleccionar' : 'Seleccionar'} agente ${name}`}
                  aria-pressed={sel}
                  style={{
                    padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                    border: sel ? '1px solid rgba(99,102,241,0.4)' : '1px solid rgba(255,255,255,0.08)',
                    background: sel ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.03)',
                    color: sel ? '#818CF8' : '#9CA3AF',
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  {sel ? '\u2713 ' : ''}{name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Input data */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#E5E7EB', display: 'block', marginBottom: 8 }}>
            Datos de entrada (JSON)
          </label>
          <textarea
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            aria-label="Datos de entrada JSON"
            rows={5}
            style={{
              width: '100%', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(0,0,0,0.2)', color: '#E5E7EB', fontSize: 13,
              fontFamily: 'monospace', resize: 'vertical', outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
            onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
          />
        </div>

        {/* Execute button */}
        <button
          onClick={handleExecute}
          disabled={executing || selectedAgents.length < 2}
          aria-label="Ejecutar swarm"
          style={{
            width: '100%', padding: '11px 0', borderRadius: 8, border: 'none',
            background: executing || selectedAgents.length < 2
              ? 'rgba(99,102,241,0.2)' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: executing || selectedAgents.length < 2 ? '#6366F1' : '#fff',
            fontSize: 14, fontWeight: 600, cursor: executing || selectedAgents.length < 2 ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s', marginBottom: 16,
          }}
        >
          {executing ? 'Ejecutando...' : selectedAgents.length < 2 ? 'Selecciona al menos 2 agentes' : 'Ejecutar Swarm'}
        </button>

        {/* Result */}
        {result && (
          <div style={{
            background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)',
            borderRadius: 10, padding: 16,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#10B981' }}>Completado</span>
              <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 'auto' }}>{result.duration}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12 }}>
              {[
                ['Topologia', result.topology],
                ['Agentes', result.agents_used],
                ['Pasos', result.steps],
              ].map(([label, val]) => (
                <div key={label} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 6, padding: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: '#9CA3AF' }}>{label}</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB' }}>{val}</div>
                </div>
              ))}
            </div>
            <p style={{ fontSize: 13, color: '#D1D5DB', margin: 0, lineHeight: 1.5 }}>{result.output}</p>
          </div>
        )}
      </div>
    </div>
  )
}
